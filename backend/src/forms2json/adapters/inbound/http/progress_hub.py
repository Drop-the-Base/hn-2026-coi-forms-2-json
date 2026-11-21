import asyncio
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from forms2json.application.ports.job_queue import JobResult, ProgressEvent


class ProgressHub:
    """Fans progress events out to the SSE streams of each job, inside the api process.

    Only the event loop touches it, so plain dicts and asyncio queues are enough.
    """

    def __init__(self) -> None:
        self._listeners: defaultdict[UUID, set[asyncio.Queue[ProgressEvent]]] = defaultdict(set)

    def publish(self, event: ProgressEvent) -> None:
        for listener in self._listeners.get(event.job_id, ()):
            listener.put_nowait(event)

    @contextmanager
    def listen(self, job_id: UUID) -> Iterator[asyncio.Queue[ProgressEvent]]:
        listener: asyncio.Queue[ProgressEvent] = asyncio.Queue()
        self._listeners[job_id].add(listener)
        try:
            yield listener
        finally:
            self._listeners[job_id].discard(listener)
            if not self._listeners[job_id]:
                del self._listeners[job_id]


def job_finished(result: JobResult) -> ProgressEvent:
    """The closing event of a stream: carries only the error type, like GET /jobs/{id}."""
    if result.error is not None:
        return ProgressEvent(result.job_id, "job", "failed", message=result.error)
    return ProgressEvent(result.job_id, "job", "done")
