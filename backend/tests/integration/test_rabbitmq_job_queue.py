import asyncio
import json
import uuid
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

import aio_pika
import pytest
from aio_pika.abc import AbstractIncomingMessage, AbstractQueue

from forms2json.adapters.outbound.queue.rabbitmq_job_queue import (
    PROGRESS,
    RESULTS,
    RabbitMqJobQueue,
)
from forms2json.adapters.outbound.storage.tmpfs_file_store import TmpfsFileStore
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.job_queue import Job
from forms2json.application.ports.pipeline_observer import PipelineObserver
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.config import Settings
from forms2json.domain.document import SourceFile


class NullObserver(PipelineObserver):
    def step(self, name: str) -> AbstractContextManager[None]:
        return nullcontext()


class Size(PipelineStep[SourceFile, dict[str, int]]):
    name = "size"

    def run(self, data: SourceFile) -> dict[str, int]:
        return {"bytes": len(data.content)}


async def first_message(queue: AbstractQueue) -> AbstractIncomingMessage:
    async with queue.iterator(no_ack=True) as messages:
        async for message in messages:
            return message
    raise AssertionError("queue closed before a message arrived")


async def round_trip(tmp_path: Path) -> None:
    url = Settings().rabbitmq_url  # RABBITMQ_URL points at a running broker
    queue = await RabbitMqJobQueue.connect(url)
    files = TmpfsFileStore(tmp_path, ttl_seconds=60)
    job = Job(uuid.uuid4(), "application/pdf")
    files.save(str(job.job_id), b"12345")

    # Plays the api: listens for this job's result and progress.
    api = await aio_pika.connect(url)
    channel = await api.channel()
    progress_queue = await channel.declare_queue(exclusive=True)
    await progress_queue.bind(PROGRESS, routing_key=str(job.job_id))
    results_queue = await channel.get_queue(RESULTS)

    try:
        await queue.consume_jobs(
            ProcessJob(files, Pipeline([Size()], NullObserver()), queue).execute
        )
        await queue.publish_job(job)

        result_message = await asyncio.wait_for(first_message(results_queue), timeout=10)
        progress_message = await asyncio.wait_for(first_message(progress_queue), timeout=10)
    finally:
        await api.close()
        await queue.close()

    assert json.loads(result_message.body) == {
        "job_id": str(job.job_id),
        "result": {"bytes": 5},
        "error": None,
    }
    assert result_message.delivery_mode == aio_pika.DeliveryMode.NOT_PERSISTENT
    assert json.loads(progress_message.body)["status"] == "done"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.integration
def test_job_goes_through_rabbitmq_to_worker_and_result_comes_back(tmp_path: Path) -> None:
    asyncio.run(round_trip(tmp_path))
