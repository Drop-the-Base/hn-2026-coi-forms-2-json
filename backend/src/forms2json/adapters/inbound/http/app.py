"""HTTP api (FR-T3). The use cases live in app.state, set by the lifespan from bootstrap.py."""

import asyncio
import hmac
from collections.abc import AsyncIterable, AsyncIterator
from typing import Annotated, Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from starlette.types import Lifespan

from forms2json.adapters.inbound.http.auth import issue_token, require_jwt
from forms2json.adapters.inbound.http.progress_hub import ProgressHub, job_finished
from forms2json.application.ports.job_queue import JobResult, ProgressEvent
from forms2json.application.ports.pdf_renderer import PreviewFailed
from forms2json.application.ports.result_store import UnknownJob
from forms2json.application.use_cases.get_job_result import GetJobResult
from forms2json.application.use_cases.render_preview import RenderPreview
from forms2json.application.use_cases.submit_job import SubmitJob
from forms2json.config import Settings, get_settings
from forms2json.domain.standards import read_schema
from forms2json.domain.upload import (
    FileTooLarge,
    InvalidFileName,
    InvalidUpload,
    UnsupportedFileType,
)


class JobAccepted(BaseModel):
    job_id: UUID


class BatchItem(BaseModel):
    file_name: str
    job_id: UUID | None = None
    error: str | None = None  # the Polish reason the file was rejected


class BatchAccepted(BaseModel):
    batch_id: UUID
    jobs: list[BatchItem]


class JobStatus(BaseModel):
    status: Literal["pending", "done", "failed"]
    result: Any = None
    error: str | None = None


class ApiConfig(BaseModel):
    max_upload_bytes: int
    max_batch_files: int


_HTTP_STATUS: dict[type[Exception], int] = {
    InvalidFileName: status.HTTP_400_BAD_REQUEST,
    FileTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
    UnsupportedFileType: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    UnknownJob: status.HTTP_404_NOT_FOUND,
    PreviewFailed: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def _error_response(request: Request, error: Exception) -> JSONResponse:
    # Upload errors already carry a Polish message for the user.
    detail = (
        "Nie ma takiego zadania albo jego wynik wygasł."
        if isinstance(error, UnknownJob)
        else str(error)
    )
    return JSONResponse({"detail": detail}, status_code=_HTTP_STATUS[type(error)])


def _submit_job(request: Request) -> SubmitJob:
    return cast(SubmitJob, request.app.state.submit_job)


def _get_job_result(request: Request) -> GetJobResult:
    return cast(GetJobResult, request.app.state.get_job_result)


def _render_preview(request: Request) -> RenderPreview:
    return cast(RenderPreview, request.app.state.render_preview)


class LoginRequest(BaseModel):
    password: str


class LoginToken(BaseModel):
    token: str


# The only /api/v1 route without require_jwt: it is how the clerk gets a token (ADR-0032).
login_router = APIRouter(prefix="/api/v1")


@login_router.post("/login", responses={401: {"description": "Nieprawidłowe hasło"}})
async def login(
    body: LoginRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> LoginToken:
    # shortcut: no rate limiting, a long random APP_PASSWORD is the defence; add it for real users.
    expected = settings.app_password.get_secret_value().encode()
    if not hmac.compare_digest(body.password.encode(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nieprawidłowe hasło.")
    return LoginToken(token=issue_token(settings, "urzednik"))


# Handlers are async on purpose: the in-memory ResultStore is then only touched by the event loop.
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_jwt)])


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    file: UploadFile,
    submit: Annotated[SubmitJob, Depends(_submit_job)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JobAccepted:
    # One byte over the limit is enough to reject the file without loading all of it.
    content = await file.read(settings.max_upload_bytes + 1)
    return JobAccepted(job_id=await submit.execute(file.filename or "", content))


@router.post(
    "/jobs/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model_exclude_none=True,
    responses={400: {"description": "Za dużo plików w jednej paczce"}},
)
async def submit_batch(
    files: list[UploadFile],
    submit: Annotated[SubmitJob, Depends(_submit_job)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BatchAccepted:
    """Batch mode (FR-E6): one job per file; a rejected file does not stop the others."""
    if len(files) > settings.max_batch_files:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Za dużo plików: {len(files)}, limit to {settings.max_batch_files} naraz.",
        )
    # shortcut: the batch id is not stored, it only groups the jobs for the client; store it
    # when someone needs GET /jobs/batch/{id}.
    jobs = []
    for file in files:
        name = file.filename or ""
        content = await file.read(settings.max_upload_bytes + 1)
        try:
            jobs.append(BatchItem(file_name=name, job_id=await submit.execute(name, content)))
        except InvalidUpload as error:
            jobs.append(BatchItem(file_name=name, error=str(error)))
    return BatchAccepted(batch_id=uuid4(), jobs=jobs)


@router.get("/jobs/{job_id}", response_model_exclude_none=True)
async def get_job(
    job_id: UUID, get_result: Annotated[GetJobResult, Depends(_get_job_result)]
) -> JobStatus:
    result = get_result.execute(job_id)
    if result is None:
        return JobStatus(status="pending")
    if result.error is not None:
        return JobStatus(status="failed", error=result.error)
    return JobStatus(status="done", result=result.result)


type _Listener = tuple[JobResult | None, asyncio.Queue[ProgressEvent]]


async def _listen(job_id: UUID, request: Request) -> AsyncIterator[_Listener]:
    hub = cast(ProgressHub, request.app.state.progress_hub)
    # Listen before reading the state, so an event arriving in between is not lost.
    with hub.listen(job_id) as events:
        # Raises UnknownJob before the stream starts, so the client gets a plain 404.
        yield _get_job_result(request).execute(job_id), events


@router.get("/jobs/{job_id}/events", response_class=EventSourceResponse)
async def job_events(
    job_id: UUID, listener: Annotated[_Listener, Depends(_listen)]
) -> AsyncIterable[ServerSentEvent]:
    """Live progress (FR-T5, ADR-0014); FastAPI adds a keep-alive ping every 15 s."""
    result, events = listener
    if result is not None:
        yield ServerSentEvent(event="progress", data=job_finished(result))
        return
    yield ServerSentEvent(event="progress", data=ProgressEvent(job_id, "job", "progress"))
    while True:
        event = await events.get()
        yield ServerSentEvent(event="progress", data=event)
        if event.step == "job":
            return


@router.get("/config")
async def get_config(settings: Annotated[Settings, Depends(get_settings)]) -> ApiConfig:
    """Limits the frontend checks before uploading (FR-05)."""
    return ApiConfig(
        max_upload_bytes=settings.max_upload_bytes, max_batch_files=settings.max_batch_files
    )


@router.get("/form-schema")
async def get_form_schema() -> dict[str, Any]:
    """The official eUsługi FormDefinition JSON Schema, as published (K-09 typo included)."""
    return read_schema()


@router.post(
    "/preview",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Plik jako PDF"},
        422: {"description": "Konwersja do PDF nie powiodła się"},
    },
)
async def render_preview(
    file: UploadFile,
    render: Annotated[RenderPreview, Depends(_render_preview)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """The uploaded DOC, DOCX, XLSX or ODS as PDF, for the review screen's original (FR-E4)."""
    content = await file.read(settings.max_upload_bytes + 1)
    pdf = await render.execute(file.filename or "", content)
    return Response(pdf, media_type="application/pdf")


@router.post(
    "/forms:convert",
    responses={202: {"model": JobAccepted}, 422: {"description": "Konwersja nie powiodła się"}},
)
async def convert_form(
    file: UploadFile,
    submit: Annotated[SubmitJob, Depends(_submit_job)],
    get_result: Annotated[GetJobResult, Depends(_get_job_result)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Any:
    """Synchronous mode (FR-01, FR-06): the eUsługi form JSON, or 202 when it takes too long."""
    content = await file.read(settings.max_upload_bytes + 1)
    job_id = await submit.execute(file.filename or "", content)
    result = await get_result.wait(job_id, settings.sync_timeout_seconds)
    if result is None:
        return JSONResponse(
            {"job_id": str(job_id)},
            status_code=status.HTTP_202_ACCEPTED,
            headers={"Location": f"/api/v1/jobs/{job_id}"},
        )
    if result.error is not None:
        return JSONResponse(
            {"detail": "Nie udało się przekonwertować formularza.", "error": result.error},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return result.result["form"]


def create_app(lifespan: Lifespan[FastAPI] | None = None) -> FastAPI:
    app = FastAPI(title="forms2json", lifespan=lifespan)
    app.include_router(login_router)
    app.include_router(router)
    for error_type in _HTTP_STATUS:
        app.add_exception_handler(error_type, _error_response)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
