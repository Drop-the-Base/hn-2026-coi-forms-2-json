import asyncio
import logging
from collections.abc import Callable

from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import Job, JobQueue, JobResult, ProgressEvent
from forms2json.domain.document import SourceFile

logger = logging.getLogger(__name__)


class ProcessJob:
    """Worker side of a job: file → pipeline → result, and the file never outlives it (NFR-06)."""

    def __init__(
        self, files: FileStore, pipelines: Callable[[], Pipeline], queue: JobQueue
    ) -> None:
        self._files = files
        self._pipelines = pipelines  # a fresh pipeline per job: steps keep per-run state
        self._queue = queue

    async def execute(self, job: Job) -> None:
        job_id = str(job.job_id)
        try:
            source = SourceFile(self._files.read(job_id), job.mime_type)
            # The pipeline blocks (LLM calls take minutes); a thread keeps AMQP heartbeats alive.
            output = await asyncio.to_thread(self._pipelines().run, source)
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
