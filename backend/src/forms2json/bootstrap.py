"""Composition root: the only place that creates concrete adapters.

Run the api: uv run uvicorn forms2json.bootstrap:create_api --factory
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from forms2json.adapters.inbound.http.app import create_app
from forms2json.adapters.outbound.queue.rabbitmq_job_queue import RabbitMqJobQueue
from forms2json.adapters.outbound.storage.in_memory_result_store import InMemoryResultStore
from forms2json.adapters.outbound.storage.tmpfs_file_store import TmpfsFileStore
from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import JobResult
from forms2json.application.use_cases.get_job_result import GetJobResult
from forms2json.application.use_cases.submit_job import SubmitJob
from forms2json.config import get_settings

FILE_CLEANUP_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


def create_api() -> FastAPI:
    return create_app(lifespan=_api_lifespan)


@asynccontextmanager
async def _api_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    files = TmpfsFileStore(settings.file_store_dir, settings.file_ttl_seconds)
    results = InMemoryResultStore(settings.result_ttl_seconds)
    queue = await RabbitMqJobQueue.connect(settings.rabbitmq_url)

    async def store_result(result: JobResult) -> None:
        results.complete(result)

    await queue.consume_results(store_result)
    cleanup = asyncio.create_task(_delete_expired_files_forever(files))
    app.state.submit_job = SubmitJob(files, queue, results, settings.max_upload_bytes)
    app.state.get_job_result = GetJobResult(results)
    try:
        yield
    finally:
        cleanup.cancel()
        await queue.close()


async def _delete_expired_files_forever(files: FileStore) -> None:
    """Removes files of jobs whose worker crashed before deleting them (ADR-0005)."""
    while True:
        try:
            files.delete_expired()
        except OSError:
            logger.exception("Deleting expired files failed, retrying later")
        await asyncio.sleep(FILE_CLEANUP_INTERVAL_SECONDS)
