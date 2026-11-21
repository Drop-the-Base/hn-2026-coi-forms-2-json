"""Composition root: the only place that creates concrete adapters (architecture.md §5)."""

from collections.abc import Callable

from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.adapters.outbound.observability.log_observer import LogObserver
from forms2json.adapters.outbound.queue.rabbitmq_job_queue import RabbitMqJobQueue
from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.adapters.outbound.readers.ods_reader import OdsReader
from forms2json.adapters.outbound.readers.xlsx_reader import XlsxReader
from forms2json.adapters.outbound.storage.tmpfs_file_store import TmpfsFileStore
from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.application.pipeline.ingest_step import IngestStep
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.report_step import ReportStep
from forms2json.application.pipeline.understand_step import UnderstandStep
from forms2json.application.pipeline.validate_step import ValidateStep
from forms2json.application.ports.llm_client import LlmClient
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.config import Settings


def pipeline_factory(settings: Settings, llm: LlmClient) -> Callable[[], Pipeline]:
    """Adapters are created once; steps per job, because Understand and Compose keep run state."""
    readers = [DocxReader(), XlsxReader(), OdsReader()]
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
