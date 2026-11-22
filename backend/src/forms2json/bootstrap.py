"""Composition root: the only place that creates concrete adapters.

Run the api: uv run uvicorn forms2json.bootstrap:create_api --factory
Run the worker: uv run python -m forms2json.adapters.inbound.worker
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from forms2json.adapters.inbound.http.app import create_app
from forms2json.adapters.inbound.http.progress_hub import ProgressHub, job_finished
from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.adapters.outbound.observability.log_observer import (
    JobLog,
    LogObserver,
    configure_logging,
)
from forms2json.adapters.outbound.observability.metrics import JobMetrics, MetricsObserver
from forms2json.adapters.outbound.observability.tracing_observer import TracingObserver
from forms2json.adapters.outbound.ocr.tesseract_ocr import TesseractOcr
from forms2json.adapters.outbound.preview.libreoffice_pdf_renderer import LibreOfficePdfRenderer
from forms2json.adapters.outbound.queue.rabbitmq_job_queue import RabbitMqJobQueue
from forms2json.adapters.outbound.readers.doc_reader import DocReader
from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.adapters.outbound.readers.image_reader import ImageReader
from forms2json.adapters.outbound.readers.ods_reader import OdsReader
from forms2json.adapters.outbound.readers.pdf_reader import PdfReader
from forms2json.adapters.outbound.readers.xlsx_reader import XlsxReader
from forms2json.adapters.outbound.storage.in_memory_result_store import InMemoryResultStore
from forms2json.adapters.outbound.storage.tmpfs_file_store import TmpfsFileStore
from forms2json.application.log_context import job_id_var
from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.application.pipeline.ingest_step import IngestStep
from forms2json.application.pipeline.pii_guard_step import PiiGuardStep
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.report_step import ReportStep
from forms2json.application.pipeline.understand_step import UnderstandStep
from forms2json.application.pipeline.validate_step import ValidateStep
from forms2json.application.ports.file_store import FileStore
from forms2json.application.ports.job_queue import JobResult, ProgressEvent
from forms2json.application.ports.llm_client import LlmClient
from forms2json.application.ports.pipeline_observer import PipelineObserver
from forms2json.application.use_cases.get_job_result import GetJobResult
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.application.use_cases.render_preview import RenderPreview
from forms2json.application.use_cases.submit_job import SubmitJob
from forms2json.config import Settings, get_settings
from forms2json.domain.cost import CostRates

FILE_CLEANUP_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


def configure_telemetry(service_name: str) -> None:
    """Exports spans and metrics over OTLP only when OTEL_EXPORTER_OTLP_ENDPOINT is set (ADR-0009).

    Without it the OTel API stays a no-op and the app runs as before.
    The exporters read the standard OTEL_EXPORTER_OTLP_* variables themselves.
    """
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    resource = Resource.create({SERVICE_NAME: service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))


def create_api() -> FastAPI:
    configure_logging("api")
    configure_telemetry("api")
    app = create_app(lifespan=_api_lifespan)
    FastAPIInstrumentor.instrument_app(app)
    return app


@asynccontextmanager
async def _api_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    files = TmpfsFileStore(settings.file_store_dir, settings.file_ttl_seconds)
    results = InMemoryResultStore(settings.result_ttl_seconds)
    queue = await RabbitMqJobQueue.connect(settings.rabbitmq_url)

    hub = ProgressHub()

    async def store_result(result: JobResult) -> None:
        job_id_var.set(str(result.job_id))
        logger.info("Result received: %s", "failed" if result.error else "done")
        results.complete(result)
        hub.publish(job_finished(result))  # closes SSE streams only once the result is readable

    async def forward_progress(event: ProgressEvent) -> None:
        # The worker's own "job" event may overtake the result (separate queues), so skip it.
        if event.step != "job":
            hub.publish(event)

    await queue.consume_results(store_result)
    await queue.consume_progress(forward_progress)
    cleanup = asyncio.create_task(_delete_expired_files_forever(files))
    app.state.submit_job = SubmitJob(files, queue, results, settings.max_upload_bytes)
    app.state.get_job_result = GetJobResult(results)
    app.state.render_preview = RenderPreview(
        LibreOfficePdfRenderer(settings.doc_conversion_timeout_seconds), settings.max_upload_bytes
    )
    app.state.progress_hub = hub
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


def pipeline_factory(settings: Settings, llm: LlmClient) -> Callable[[PipelineObserver], Pipeline]:
    """Adapters are created once; steps per job, because PiiGuard, Understand and Compose keep run
    state."""
    ocr = TesseractOcr(settings.ocr_lang)
    readers = [
        DocxReader(),
        DocReader(settings.doc_conversion_timeout_seconds),
        XlsxReader(),
        OdsReader(),
        PdfReader(ocr),
        ImageReader(ocr),
    ]
    tracing, logs, step_metrics = TracingObserver(), LogObserver(), MetricsObserver()

    def new_pipeline(progress: PipelineObserver) -> Pipeline:
        pii = PiiGuardStep()
        understand = UnderstandStep(llm, settings.llm_max_input_chars)
        compose = ComposeStep()
        report = ReportStep(
            pii, understand, compose, settings.confidence_review_threshold, cost_rates(settings)
        )
        return Pipeline(
            [IngestStep(readers), pii, understand, compose, ValidateStep(), report],
            tracing,
            logs,
            step_metrics,
            progress,
        )

    return new_pipeline


def new_llm_client(settings: Settings) -> LlmClient:
    return OpenAiCompatibleLlmClient(
        settings.llm_base_url,
        settings.llm_model,
        settings.llm_timeout_seconds,
        settings.llm_max_output_tokens,
        api_key=settings.llm_api_key.get_secret_value(),
        response_format=settings.llm_response_format,
        cost_rates=cost_rates(settings),
    )


def cost_rates(settings: Settings) -> CostRates:
    return CostRates(
        settings.cost_per_1m_input_tokens,
        settings.cost_per_1m_output_tokens,
        settings.cost_per_gpu_second,
        settings.cost_currency,
    )


async def build_worker(settings: Settings) -> tuple[RabbitMqJobQueue, ProcessJob]:
    configure_logging("worker")
    configure_telemetry("worker")
    queue = await RabbitMqJobQueue.connect(settings.rabbitmq_url)
    files = TmpfsFileStore(settings.file_store_dir, settings.file_ttl_seconds)
    pipelines = pipeline_factory(settings, new_llm_client(settings))
    return queue, ProcessJob(files, pipelines, queue, [JobMetrics(settings.llm_model), JobLog()])
