from abc import ABC, abstractmethod

from forms2json.application.ports.job_queue import JobResult


class JobObserver(ABC):
    """Sees every finished job, done or failed: the place for job metrics (NFR-13, NFR-14)."""

    @abstractmethod
    def job_finished(self, result: JobResult, seconds: float) -> None: ...
