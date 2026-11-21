import asyncio
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Literal
from uuid import UUID

from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import Job, JobQueue, JobResult, ProgressEvent
from forms2json.application.ports.pipeline_observer import PipelineObserver
from forms2json.domain.document import SourceFile

PROGRESS_PUBLISH_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


class ProcessJob:
    """Worker side of a job: file → pipeline → result, and the file never outlives it (NFR-06)."""

    def __init__(
        self,
        files: FileStore,
        pipelines: Callable[[PipelineObserver], Pipeline],
        queue: JobQueue,
    ) -> None:
        self._files = files
        # A fresh pipeline per job: steps keep per-run state, and progress belongs to the job.
        self._pipelines = pipelines
        self._queue = queue

    async def execute(self, job: Job) -> None:
        job_id = str(job.job_id)
        progress = _ProgressObserver(job.job_id, self._queue, asyncio.get_running_loop())
        try:
            source = SourceFile(self._files.read(job_id), job.mime_type)
            # The pipeline blocks (LLM calls take minutes); a thread keeps AMQP heartbeats alive.
            output = await asyncio.to_thread(self._pipelines(progress).run, source)
            result = JobResult(job.job_id, result=output)
        except Exception as error:
            logger.exception("Job %s failed", job_id)
            # Only the type: parser messages may quote document content.
            result = JobResult(job.job_id, error=type(error).__name__)
        finally:
            self._files.delete(job_id)

        await self._queue.publish_result(result)
        await self._queue.publish_progress(
            ProgressEvent(job.job_id, step="job", status="failed" if result.error else "done")
        )


class _ProgressObserver(PipelineObserver):
    """Publishes started/done/failed per step from the pipeline thread (ADR-0014)."""

    def __init__(self, job_id: UUID, queue: JobQueue, loop: asyncio.AbstractEventLoop) -> None:
        self._job_id = job_id
        self._queue = queue
        self._loop = loop

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        self._publish(name, "started")
        try:
            yield
        except Exception:
            self._publish(name, "failed")  # no message: it may quote document content
            raise
        self._publish(name, "done")

    def _publish(self, step: str, status: Literal["started", "done", "failed"]) -> None:
        event = ProgressEvent(self._job_id, step, status)
        # Waiting for each publish keeps events in order; the loop is free while we wait.
        future = asyncio.run_coroutine_threadsafe(self._queue.publish_progress(event), self._loop)
        try:
            future.result(PROGRESS_PUBLISH_TIMEOUT_SECONDS)
        except Exception:
            # Progress is best effort: a lost event must not fail the job.
            logger.warning("Publishing progress of job %s failed", self._job_id, exc_info=True)
