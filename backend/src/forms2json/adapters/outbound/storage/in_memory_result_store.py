import time
from collections.abc import Callable
from uuid import UUID

from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.result_store import ResultStore, UnknownJob


class InMemoryResultStore(ResultStore):
    """A dict in the api process: results vanish after the TTL or an api restart (NFR-06).

    shortcut: one api replica only (results are not shared), move to Valkey when scaling out.
    """

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[UUID, tuple[float, JobResult | None]] = {}

    def add_pending(self, job_id: UUID) -> None:
        self._put(job_id, None)

    def complete(self, result: JobResult) -> None:
        self._put(result.job_id, result)  # the TTL restarts, so the result gets its full TTL

    def get(self, job_id: UUID) -> JobResult | None:
        self._drop_expired()
        try:
            return self._entries[job_id][1]
        except KeyError:
            raise UnknownJob(job_id) from None

    def _put(self, job_id: UUID, result: JobResult | None) -> None:
        self._drop_expired()
        self._entries[job_id] = (self._clock() + self._ttl_seconds, result)

    def _drop_expired(self) -> None:
        now = self._clock()
        expired = [job_id for job_id, (expires, _) in self._entries.items() if expires <= now]
        for job_id in expired:
            del self._entries[job_id]
