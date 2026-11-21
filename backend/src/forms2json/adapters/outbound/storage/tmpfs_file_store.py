import os
import time
import uuid
from pathlib import Path

from forms2json.application.ports.file_store import FileStore


class TmpfsFileStore(FileStore):
    """One file per job in a directory mounted as tmpfs in compose, so bytes never hit disk."""

    def __init__(self, directory: Path, ttl_seconds: int) -> None:
        self._directory = directory
        self._ttl_seconds = ttl_seconds
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)

    def save(self, job_id: str, content: bytes) -> None:
        path = self._path(job_id)
        # O_EXCL | O_NOFOLLOW: never overwrite another job's file or follow a planted symlink.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as file:
                file.write(content)
        except BaseException:
            path.unlink(missing_ok=True)  # a half-written file must not outlive the failed save
            raise

    def read(self, job_id: str) -> bytes:
        return self._path(job_id).read_bytes()

    def delete(self, job_id: str) -> None:
        self._path(job_id).unlink(missing_ok=True)

    def delete_expired(self) -> None:
        # shortcut: nothing calls this periodically yet; schedule it in the api lifespan
        # once the FastAPI app exists (ADR-0005).
        cutoff = time.time() - self._ttl_seconds
        for path in self._directory.iterdir():
            try:
                if path.lstat().st_mtime < cutoff:
                    path.unlink()
            except FileNotFoundError:
                pass  # the worker deleted it between iterdir and unlink

    def _path(self, job_id: str) -> Path:
        # job_id ends up in a path: accept only a UUID and use its canonical form (no traversal).
        try:
            name = str(uuid.UUID(job_id))
        except ValueError:
            raise ValueError(f"job_id must be a UUID, got {job_id!r}") from None
        return self._directory / name
