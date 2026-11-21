import uuid

import pytest

from forms2json.adapters.outbound.storage.in_memory_result_store import InMemoryResultStore
from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.result_store import UnknownJob


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_pending_then_done() -> None:
    store = InMemoryResultStore(ttl_seconds=10)
    job_id = uuid.uuid4()

    store.add_pending(job_id)
    assert store.get(job_id) is None

    store.complete(JobResult(job_id, result={"ok": True}))
    assert store.get(job_id) == JobResult(job_id, result={"ok": True})


def test_unknown_job_raises() -> None:
    with pytest.raises(UnknownJob):
        InMemoryResultStore(ttl_seconds=10).get(uuid.uuid4())


def test_result_expires_after_ttl_counted_from_completion() -> None:
    clock = Clock()
    store = InMemoryResultStore(ttl_seconds=10, clock=clock)
    job_id = uuid.uuid4()
    store.add_pending(job_id)

    clock.now = 8
    store.complete(JobResult(job_id, result=1))
    clock.now = 17
    assert store.get(job_id) == JobResult(job_id, result=1)

    clock.now = 18
    with pytest.raises(UnknownJob):
        store.get(job_id)
