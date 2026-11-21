import uuid
from uuid import UUID

from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import Job, JobQueue
from forms2json.application.ports.result_store import ResultStore
from forms2json.domain.upload import validate_upload


class SubmitJob:
    """Api side of a job: validate → store the file → queue the job (FR-T3, NFR-06)."""

    def __init__(
        self, files: FileStore, queue: JobQueue, results: ResultStore, max_upload_bytes: int
    ) -> None:
        self._files = files
        self._queue = queue
        self._results = results
        self._max_upload_bytes = max_upload_bytes

    async def execute(self, filename: str, content: bytes) -> UUID:
        mime_type = validate_upload(filename, content, self._max_upload_bytes)
        job_id = uuid.uuid4()
        self._files.save(str(job_id), content)
        # Pending before publish, so it can never overwrite a result from a fast worker.
        self._results.add_pending(job_id)
        try:
            await self._queue.publish_job(Job(job_id, mime_type))
        except BaseException:
            self._files.delete(str(job_id))  # nobody will process it, so it must not linger
            raise
        return job_id
