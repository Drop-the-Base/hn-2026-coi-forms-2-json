"""HTTP api (FR-T3). The use cases live in app.state, set by the lifespan from bootstrap.py."""

from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.types import Lifespan

from forms2json.adapters.inbound.http.auth import require_jwt
from forms2json.application.ports.result_store import UnknownJob
from forms2json.application.use_cases.get_job_result import GetJobResult
from forms2json.application.use_cases.submit_job import SubmitJob
from forms2json.config import Settings, get_settings
from forms2json.domain.upload import FileTooLarge, InvalidFileName, UnsupportedFileType


class JobAccepted(BaseModel):
    job_id: UUID


class JobStatus(BaseModel):
    status: Literal["pending", "done", "failed"]
    result: Any = None
    error: str | None = None


class ApiConfig(BaseModel):
    max_upload_bytes: int


_HTTP_STATUS: dict[type[Exception], int] = {
    InvalidFileName: status.HTTP_400_BAD_REQUEST,
    FileTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
    UnsupportedFileType: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    UnknownJob: status.HTTP_404_NOT_FOUND,
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


@router.get("/config")
async def get_config(settings: Annotated[Settings, Depends(get_settings)]) -> ApiConfig:
    """Limits the frontend checks before uploading (FR-05)."""
    return ApiConfig(max_upload_bytes=settings.max_upload_bytes)


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
    app.include_router(router)
    for error_type in _HTTP_STATUS:
        app.add_exception_handler(error_type, _error_response)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
