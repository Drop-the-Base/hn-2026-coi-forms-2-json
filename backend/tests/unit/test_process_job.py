import asyncio
import uuid
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, nullcontext

from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import Job, JobQueue, JobResult, ProgressEvent
from forms2json.application.ports.pipeline_observer import PipelineObserver
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.domain.document import SourceFile


class FakeFileStore(FileStore):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, job_id: str, content: bytes) -> None:
        self.files[job_id] = content

    def read(self, job_id: str) -> bytes:
        return self.files[job_id]

    def delete(self, job_id: str) -> None:
        self.files.pop(job_id, None)

    def delete_expired(self) -> None:
        pass


class FakeJobQueue(JobQueue):
    def __init__(self) -> None:
        self.jobs: list[Job] = []
        self.results: list[JobResult] = []
        self.events: list[ProgressEvent] = []

    async def publish_job(self, job: Job) -> None:
        self.jobs.append(job)

    async def consume_jobs(self, handler: Callable[[Job], Awaitable[None]]) -> None:
        raise NotImplementedError

    async def publish_result(self, result: JobResult) -> None:
        self.results.append(result)

    async def consume_results(self, handler: Callable[[JobResult], Awaitable[None]]) -> None:
        raise NotImplementedError

    async def publish_progress(self, event: ProgressEvent) -> None:
        self.events.append(event)


class NullObserver(PipelineObserver):
    def step(self, name: str) -> AbstractContextManager[None]:
        return nullcontext()


class Describe(PipelineStep[SourceFile, str]):
    name = "describe"

    def run(self, data: SourceFile) -> str:
        return f"{data.mime_type}:{data.content.decode()}"


class Boom(PipelineStep[SourceFile, str]):
    name = "boom"

    def run(self, data: SourceFile) -> str:
        raise ValueError("secret document text")


def run_job(step: PipelineStep[SourceFile, str]) -> tuple[FakeFileStore, FakeJobQueue, Job]:
    files, queue = FakeFileStore(), FakeJobQueue()
    job = Job(uuid.uuid4(), "application/pdf")
    files.save(str(job.job_id), b"form")
    use_case = ProcessJob(files, Pipeline([step], NullObserver()), queue)

    asyncio.run(use_case.execute(job))
    return files, queue, job


def test_success_publishes_pipeline_output_and_deletes_file() -> None:
    files, queue, job = run_job(Describe())

    assert queue.results == [JobResult(job.job_id, result="application/pdf:form")]
    assert [(e.step, e.status) for e in queue.events] == [("job", "done")]
    assert files.files == {}


def test_failing_step_publishes_error_without_its_message_and_deletes_file() -> None:
    files, queue, job = run_job(Boom())

    assert queue.results == [JobResult(job.job_id, error="ValueError")]
    assert [(e.step, e.status) for e in queue.events] == [("job", "failed")]
    assert files.files == {}


def test_missing_file_publishes_error() -> None:
    files, queue = FakeFileStore(), FakeJobQueue()
    job = Job(uuid.uuid4(), "application/pdf")

    asyncio.run(ProcessJob(files, Pipeline([Describe()], NullObserver()), queue).execute(job))

    assert queue.results == [JobResult(job.job_id, error="KeyError")]
