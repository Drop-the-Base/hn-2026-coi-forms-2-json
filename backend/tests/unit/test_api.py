import asyncio
import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from forms2json.adapters.inbound.http.app import create_app
from forms2json.adapters.inbound.http.auth import issue_token
from forms2json.adapters.inbound.http.progress_hub import ProgressHub, job_finished
from forms2json.adapters.outbound.storage.in_memory_result_store import InMemoryResultStore
from forms2json.application.ports.job_queue import Job, JobResult, ProgressEvent
from forms2json.application.use_cases.get_job_result import GetJobResult
from forms2json.application.use_cases.submit_job import SubmitJob
from forms2json.config import Settings, get_settings
from tests.unit.test_process_job import FakeFileStore, FakeJobQueue

PDF = b"%PDF-1.7\nform"
MAX_BYTES = 64


class Api:
    def __init__(self) -> None:
        settings = Settings(max_upload_bytes=MAX_BYTES)
        self.files, self.queue = FakeFileStore(), FakeJobQueue()
        self.results = InMemoryResultStore(ttl_seconds=60)
        self.app = app = create_app()
        app.state.submit_job = SubmitJob(self.files, self.queue, self.results, MAX_BYTES)
        app.state.get_job_result = GetJobResult(self.results)
        self.hub = app.state.progress_hub = ProgressHub()
        app.dependency_overrides[get_settings] = lambda: settings
        self.client = TestClient(app)
        self.client.headers["Authorization"] = f"Bearer {issue_token(settings, 'test')}"

    def upload(self, name: str, content: bytes) -> tuple[int, dict[str, str]]:
        response = self.client.post("/api/v1/jobs", files={"file": (name, content)})
        return response.status_code, response.json()


@pytest.fixture
def api() -> Api:
    return Api()


def test_endpoints_without_token_are_401(api: Api) -> None:
    del api.client.headers["Authorization"]
    assert api.client.post("/api/v1/jobs", files={"file": ("a.pdf", PDF)}).status_code == 401
    assert api.client.get(f"/api/v1/jobs/{uuid.uuid4()}").status_code == 401
    assert api.client.get("/api/v1/config").status_code == 401
    assert api.client.get("/api/v1/form-schema").status_code == 401
    assert api.queue.jobs == []


def test_health_needs_no_token(api: Api) -> None:
    del api.client.headers["Authorization"]
    assert api.client.get("/health").json() == {"status": "ok"}


def test_valid_upload_is_stored_queued_and_pending(api: Api) -> None:
    status, body = api.upload("wniosek.pdf", PDF)

    assert status == 202
    job_id = uuid.UUID(body["job_id"])
    assert api.files.files == {str(job_id): PDF}
    assert api.queue.jobs == [Job(job_id, "application/pdf")]
    assert api.client.get(f"/api/v1/jobs/{job_id}").json() == {"status": "pending"}


@pytest.mark.parametrize(
    ("name", "content", "status"),
    [
        ("wniosek;1.pdf", PDF, 400),
        ("wniosek.exe", PDF, 415),
        ("wniosek.pdf", b"\x89PNG\r\n\x1a\nnot a pdf", 415),
        ("wniosek.pdf", PDF + b"x" * MAX_BYTES, 413),
    ],
)
def test_invalid_upload_is_rejected_with_polish_message(
    api: Api, name: str, content: bytes, status: int
) -> None:
    code, body = api.upload(name, content)

    assert code == status
    assert body["detail"].startswith(("Nazwa", "Nieobsługiwany", "Zawartość", "Plik"))
    assert api.files.files == {}
    assert api.queue.jobs == []


def test_done_and_failed_results(api: Api) -> None:
    done, failed = uuid.uuid4(), uuid.uuid4()
    api.results.complete(JobResult(done, result={"title": "Wniosek"}))
    api.results.complete(JobResult(failed, error="ValueError"))

    assert api.client.get(f"/api/v1/jobs/{done}").json() == {
        "status": "done",
        "result": {"title": "Wniosek"},
    }
    assert api.client.get(f"/api/v1/jobs/{failed}").json() == {
        "status": "failed",
        "error": "ValueError",
    }


def test_unknown_job_is_404(api: Api) -> None:
    response = api.client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "zadania" in response.json()["detail"]


def test_config_exposes_upload_limit(api: Api) -> None:
    assert api.client.get("/api/v1/config").json() == {"max_upload_bytes": MAX_BYTES}


def test_form_schema_is_the_official_schema_as_published(api: Api) -> None:
    schema = api.client.get("/api/v1/form-schema").json()
    assert schema["title"] == "FormDefinition"
    assert "repetingSectionGrid" in json.dumps(schema)


def sse_events(api: Api, job_id: uuid.UUID) -> list[dict[str, Any]]:
    response = api.client.get(f"/api/v1/jobs/{job_id}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in response.text.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "data" in lines:
            assert lines["event"] == "progress"
            events.append(json.loads(lines["data"]))
    return events


def test_events_of_finished_job_send_final_event_and_close(api: Api) -> None:
    done, failed = uuid.uuid4(), uuid.uuid4()
    api.results.complete(JobResult(done, result={"title": "Wniosek"}))
    api.results.complete(JobResult(failed, error="ValueError"))

    [done_event] = sse_events(api, done)
    [failed_event] = sse_events(api, failed)

    assert done_event | {"ts": 0} == {
        "job_id": str(done),
        "step": "job",
        "status": "done",
        "message": "",
        "ts": 0,
    }
    assert (failed_event["status"], failed_event["message"]) == ("failed", "ValueError")


class ReplayingHub(ProgressHub):
    """Plays the broker: delivers the given events as soon as a stream starts listening."""

    def __init__(self, events: list[ProgressEvent]) -> None:
        super().__init__()
        self.events = events

    @contextmanager
    def listen(self, job_id: uuid.UUID) -> Iterator[asyncio.Queue[ProgressEvent]]:
        with super().listen(job_id) as listener:
            for event in self.events:
                self.publish(event)
            yield listener


def test_events_of_running_job_are_forwarded_in_order_until_the_end(api: Api) -> None:
    job_id, other_job = uuid.uuid4(), uuid.uuid4()
    api.results.add_pending(job_id)
    api.hub = api.app.state.progress_hub = ReplayingHub(
        [
            ProgressEvent(job_id, "ingest", "started"),
            ProgressEvent(other_job, "ingest", "started"),
            ProgressEvent(job_id, "ingest", "done"),
            job_finished(JobResult(job_id, result={})),
            ProgressEvent(job_id, "late", "started"),
        ]
    )

    events = sse_events(api, job_id)

    assert [(e["job_id"], e["step"], e["status"]) for e in events] == [
        (str(job_id), "job", "progress"),
        (str(job_id), "ingest", "started"),
        (str(job_id), "ingest", "done"),
        (str(job_id), "job", "done"),
    ]
    assert api.hub._listeners == {}


def test_events_need_token_and_known_job(api: Api) -> None:
    assert api.client.get(f"/api/v1/jobs/{uuid.uuid4()}/events").status_code == 404
    del api.client.headers["Authorization"]
    assert api.client.get(f"/api/v1/jobs/{uuid.uuid4()}/events").status_code == 401


class BrokenQueue(FakeJobQueue):
    async def publish_job(self, job: Job) -> None:
        raise ConnectionError


def test_file_is_deleted_when_the_job_cannot_be_queued() -> None:
    files = FakeFileStore()
    submit = SubmitJob(files, BrokenQueue(), InMemoryResultStore(ttl_seconds=60), MAX_BYTES)

    with pytest.raises(ConnectionError):
        asyncio.run(submit.execute("wniosek.pdf", PDF))
    assert files.files == {}


class InstantWorker(FakeJobQueue):
    """Completes every job as soon as it is queued, like a very fast worker."""

    def __init__(self, results: InMemoryResultStore, outcome: JobResult) -> None:
        super().__init__()
        self._results, self._outcome = results, outcome

    async def publish_job(self, job: Job) -> None:
        await super().publish_job(job)
        self._results.complete(JobResult(job.job_id, self._outcome.result, self._outcome.error))


def convert(api: Api, outcome: JobResult | None, timeout: float = 5.0) -> httpx2.Response:
    settings = Settings(max_upload_bytes=MAX_BYTES, sync_timeout_seconds=timeout)
    api.app.dependency_overrides[get_settings] = lambda: settings
    queue = InstantWorker(api.results, outcome) if outcome else api.queue
    api.app.state.submit_job = SubmitJob(api.files, queue, api.results, MAX_BYTES)
    return api.client.post("/api/v1/forms:convert", files={"file": ("wniosek.pdf", PDF)})


def test_convert_returns_the_form_json(api: Api) -> None:
    form = {"title": "Wniosek", "pages": []}
    response = convert(api, JobResult(uuid.uuid4(), result={"form": form, "confidence": 0.9}))

    assert response.status_code == 200
    assert response.json() == form


def test_convert_failed_job_is_422(api: Api) -> None:
    response = convert(api, JobResult(uuid.uuid4(), error="ValueError"))

    assert response.status_code == 422
    assert response.json()["error"] == "ValueError"


def test_convert_timeout_is_202_with_job_location(api: Api) -> None:
    response = convert(api, None, timeout=0.05)

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.headers["Location"] == f"/api/v1/jobs/{job_id}"
    assert api.client.get(response.headers["Location"]).json() == {"status": "pending"}


def test_wait_returns_a_result_that_arrives_later() -> None:
    results, job_id = InMemoryResultStore(ttl_seconds=60), uuid.uuid4()
    results.add_pending(job_id)

    async def scenario() -> JobResult | None:
        asyncio.get_running_loop().call_later(0.05, results.complete, JobResult(job_id, result=1))
        return await GetJobResult(results).wait(job_id, timeout_seconds=5)

    assert asyncio.run(scenario()) == JobResult(job_id, result=1)


def test_convert_without_token_is_401(api: Api) -> None:
    del api.client.headers["Authorization"]
    response = api.client.post("/api/v1/forms:convert", files={"file": ("a.pdf", PDF)})
    assert response.status_code == 401
    assert api.queue.jobs == []


def test_convert_rejects_a_bad_file(api: Api) -> None:
    response = api.client.post("/api/v1/forms:convert", files={"file": ("wniosek.exe", PDF)})
    assert response.status_code == 415
    assert api.queue.jobs == []
