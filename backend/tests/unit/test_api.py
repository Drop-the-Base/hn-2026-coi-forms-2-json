import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from forms2json.adapters.inbound.http.app import create_app
from forms2json.adapters.inbound.http.auth import issue_token
from forms2json.adapters.outbound.storage.in_memory_result_store import InMemoryResultStore
from forms2json.application.ports.job_queue import Job, JobResult
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
        app = create_app()
        app.state.submit_job = SubmitJob(self.files, self.queue, self.results, MAX_BYTES)
        app.state.get_job_result = GetJobResult(self.results)
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


class BrokenQueue(FakeJobQueue):
    async def publish_job(self, job: Job) -> None:
        raise ConnectionError


def test_file_is_deleted_when_the_job_cannot_be_queued() -> None:
    files = FakeFileStore()
    submit = SubmitJob(files, BrokenQueue(), InMemoryResultStore(ttl_seconds=60), MAX_BYTES)

    with pytest.raises(ConnectionError):
        asyncio.run(submit.execute("wniosek.pdf", PDF))
    assert files.files == {}
