from abc import ABC, abstractmethod


class FileStore(ABC):
    """Holds an uploaded file only while its job runs (NFR-06, ADR-0005)."""

    @abstractmethod
    def save(self, job_id: str, content: bytes) -> None: ...

    @abstractmethod
    def read(self, job_id: str) -> bytes: ...

    @abstractmethod
    def delete(self, job_id: str) -> None:
        """Idempotent: deleting a missing file is not an error."""

    @abstractmethod
    def delete_expired(self) -> None:
        """Removes files left behind by jobs that crashed before their own delete."""
