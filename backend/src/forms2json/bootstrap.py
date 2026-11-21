"""Composition root: the only place that creates concrete adapters.

Run the api: uv run uvicorn forms2json.bootstrap:create_api --factory
Run the worker: uv run python -m forms2json.adapters.inbound.worker
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from forms2json.adapters.inbound.http.app import create_app
from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.adapters.outbound.observability.log_observer import LogObserver
from forms2json.adapters.outbound.queue.rabbitmq_job_queue import RabbitMqJobQueue
from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.adapters.outbound.readers.ods_reader import OdsReader
from forms2json.adapters.outbound.readers.pdf_reader import PdfReader
from forms2json.adapters.outbound.readers.xlsx_reader import XlsxReader
from forms2json.adapters.outbound.storage.in_memory_result_store import InMemoryResultStore
from forms2json.adapters.outbound.storage.tmpfs_file_store import TmpfsFileStore
from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.application.pipeline.ingest_step import IngestStep
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.report_step import ReportStep
from forms2json.application.pipeline.understand_step import UnderstandStep
from forms2json.application.pipeline.validate_step import ValidateStep
from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.llm_client import LlmClient
from forms2json.application.use_cases.get_job_result import GetJobResult
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.application.use_cases.submit_job import SubmitJob
from forms2json.config import Settings, get_settings

FILE_CLEANUP_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


def create_api() -> FastAPI:
    return create_app(lifespan=_api_lifespan)


@asynccontextmanager
async def _api_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    files = TmpfsFileStore(settings.file_store_dir, settings.file_ttl_seconds)
    results = InMemoryResultStore(settings.result_ttl_seconds)
    queue = await RabbitMqJobQueue.connect(settings.rabbitmq_url)

    async def store_result(result: JobResult) -> None:
        results.complete(result)

    await queue.consume_results(store_result)
    cleanup = asyncio.create_task(_delete_expired_files_forever(files))
    app.state.submit_job = SubmitJob(files, queue, results, settings.max_upload_bytes)
    app.state.get_job_result = GetJobResult(results)
    try:
        yield
    finally:
        cleanup.cancel()
        await queue.close()


async def _delete_expired_files_forever(files: FileStore) -> None:
    """Removes files of jobs whose worker crashed before deleting them (ADR-0005)."""
    while True:
        try:
            files.delete_expired()
        except OSError:
            logger.exception("Deleting expired files failed, retrying later")
        await asyncio.sleep(FILE_CLEANUP_INTERVAL_SECONDS)


def pipeline_factory(settings: Settings, llm: LlmClient) -> Callable[[], Pipeline]:
    """Adapters are created once; steps per job, because Understand and Compose keep run state."""
    readers = [DocxReader(), XlsxReader(), OdsReader(), PdfReader()]
    observer = LogObserver()

    def new_pipeline() -> Pipeline:
        understand = UnderstandStep(llm, settings.llm_max_input_chars)
        compose = ComposeStep()
        report = ReportStep(understand, compose, settings.confidence_review_threshold)
        return Pipeline(
            [IngestStep(readers), understand, compose, ValidateStep(), report], observer
        )

    return new_pipeline


def new_llm_client(settings: Settings) -> LlmClient:
    return OpenAiCompatibleLlmClient(
        settings.llm_base_url, settings.llm_model, settings.llm_timeout_seconds
    )


async def build_worker(settings: Settings) -> tuple[RabbitMqJobQueue, ProcessJob]:
    queue = await RabbitMqJobQueue.connect(settings.rabbitmq_url)
    files = TmpfsFileStore(settings.file_store_dir, settings.file_ttl_seconds)
    pipelines = pipeline_factory(settings, new_llm_client(settings))
    return queue, ProcessJob(files, pipelines, queue)
