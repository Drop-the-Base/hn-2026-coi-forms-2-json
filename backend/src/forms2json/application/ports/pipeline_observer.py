from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class PipelineObserver(ABC):
    """Watches step boundaries: one place for the OTel span and the progress event (ADR-0014)."""

    @abstractmethod
    def step(self, name: str) -> AbstractContextManager[None]:
        """Entered before the step runs, exited after it; an exception means the step failed."""
