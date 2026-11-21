import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID


@dataclass(frozen=True)
class Job:
    """Only the id and type travel through the broker; the bytes stay in FileStore (NFR-06)."""

    job_id: UUID
    mime_type: str


@dataclass(frozen=True)
class JobResult:
    job_id: UUID
    result: Any = None  # pipeline output, serialized to JSON by the adapter
    error: str | None = None


@dataclass(frozen=True)
class ProgressEvent:
    """Pipeline progress for the SSE stream (ADR-0014). Never carries file content."""

    job_id: UUID
    step: str
    status: Literal["started", "progress", "done", "failed"]
    message: str = ""
    ts: float = field(default_factory=time.time)


class JobQueue(ABC):
    """Hands jobs from api to worker and results back (ADR-0004)."""

    @abstractmethod
    async def publish_job(self, job: Job) -> None: ...

    @abstractmethod
    async def consume_jobs(self, handler: Callable[[Job], Awaitable[None]]) -> None:
        """Registers the handler and returns; jobs then arrive one at a time."""

    @abstractmethod
    async def publish_result(self, result: JobResult) -> None: ...

    @abstractmethod
    async def consume_results(self, handler: Callable[[JobResult], Awaitable[None]]) -> None:
        """Registers the handler and returns; results then arrive one at a time."""

    @abstractmethod
    async def publish_progress(self, event: ProgressEvent) -> None: ...
