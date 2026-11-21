from abc import ABC, abstractmethod
from uuid import UUID

from forms2json.application.ports.job_queue import JobResult


class UnknownJob(LookupError):
    """No such job, or its result already expired."""


class ResultStore(ABC):
    """Job results kept only for a while in the api process (NFR-06)."""

    @abstractmethod
    def add_pending(self, job_id: UUID) -> None: ...

    @abstractmethod
    def complete(self, result: JobResult) -> None: ...

    @abstractmethod
    def get(self, job_id: UUID) -> JobResult | None:
        """None while the job is pending; raises UnknownJob for an unknown or expired job."""
