import pytest
from fastapi.testclient import TestClient

from forms2json.adapters.inbound.http.app import create_app
from forms2json.adapters.inbound.http.auth import issue_token
from forms2json.adapters.outbound.libreoffice import SofficeFailed
from forms2json.adapters.outbound.preview.libreoffice_pdf_renderer import LibreOfficePdfRenderer
from forms2json.application.ports.pdf_renderer import PdfRenderer, PreviewFailed
from forms2json.application.use_cases.render_preview import RenderPreview
from forms2json.config import Settings, get_settings
from forms2json.domain.upload import DOC, DOCX, ODS, XLSX

from .test_docx_reader import docx

MAX_BYTES = 4096
PDF = b"%PDF-1.7\npreview"


class FakePdfRenderer(PdfRenderer):
    def __init__(self, error: PreviewFailed | None = None) -> None:
        self.calls: list[str] = []
        self._error = error

    def render(self, content: bytes, mime_type: str) -> bytes:
        self.calls.append(mime_type)
        if self._error:
            raise self._error
        return PDF


def client_for(renderer: PdfRenderer) -> TestClient:
    settings = Settings(max_upload_bytes=MAX_BYTES)
    app = create_app()
    app.state.render_preview = RenderPreview(renderer, MAX_BYTES)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {issue_token(settings, 'test')}"
    return client


@pytest.fixture
def renderer() -> FakePdfRenderer:
    return FakePdfRenderer()


@pytest.fixture
def client(renderer: FakePdfRenderer) -> TestClient:
    return client_for(renderer)


def preview(client: TestClient, name: str, content: bytes) -> tuple[int, str, bytes]:
    response = client.post("/api/v1/preview", files={"file": (name, content)})
    return response.status_code, response.headers["content-type"], response.content


def test_office_file_comes_back_as_pdf(client: TestClient, renderer: FakePdfRenderer) -> None:
    status, content_type, body = preview(client, "wniosek.docx", docx("<w:p/>"))

    assert (status, content_type, body) == (200, "application/pdf", PDF)
    assert renderer.calls == [DOCX]


def test_needs_a_token(client: TestClient, renderer: FakePdfRenderer) -> None:
    del client.headers["Authorization"]
    assert preview(client, "wniosek.docx", docx("<w:p/>"))[0] == 401
    assert renderer.calls == []


@pytest.mark.parametrize(
    ("name", "content", "status"),
    [
        ("wniosek;1.docx", b"x", 400),
        ("wniosek.exe", b"x", 415),
        ("wniosek.docx", b"%PDF-1.7 not a docx", 415),
        ("wniosek.pdf", PDF, 415),  # the browser shows PDF by itself
        ("wniosek.docx", b"x" * (MAX_BYTES + 1), 413),
    ],
)
def test_invalid_upload_is_rejected_before_rendering(
    client: TestClient, renderer: FakePdfRenderer, name: str, content: bytes, status: int
) -> None:
    assert preview(client, name, content)[0] == status
    assert renderer.calls == []


def test_failed_rendering_is_422_with_the_message() -> None:
    client = client_for(FakePdfRenderer(PreviewFailed("Nie udało się.")))

    response = client.post("/api/v1/preview", files={"file": ("a.docx", docx("<w:p/>"))})

    assert response.status_code == 422
    assert response.json() == {"detail": "Nie udało się."}


@pytest.mark.parametrize(
    ("mime_type", "suffix"), [(DOC, ".doc"), (DOCX, ".docx"), (XLSX, ".xlsx"), (ODS, ".ods")]
)
def test_libreoffice_renderer_converts_to_pdf(mime_type: str, suffix: str) -> None:
    calls: list[tuple[bytes, str, str, float]] = []

    def convert(content: bytes, suffix: str, target: str, timeout: float) -> bytes:
        calls.append((content, suffix, target, timeout))
        return PDF

    assert LibreOfficePdfRenderer(9.0, convert).render(b"file", mime_type) == PDF
    assert calls == [(b"file", suffix, "pdf", 9.0)]


def test_libreoffice_failure_becomes_preview_failed() -> None:
    def convert(content: bytes, suffix: str, target: str, timeout: float) -> bytes:
        raise SofficeFailed("timeout")

    with pytest.raises(PreviewFailed):
        LibreOfficePdfRenderer(1.0, convert).render(b"file", DOC)
