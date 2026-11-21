import logging
import os
import sys
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace

from forms2json.application.log_context import job_id_var
from forms2json.application.ports.job_observer import JobObserver
from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.pipeline_observer import PipelineObserver

logger = logging.getLogger(__name__)


class JobContextFilter(logging.Filter):
    """Adds job_id and the current OTel trace_id, so a log line leads to its trace in Jaeger."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = job_id_var.get()
        context = trace.get_current_span().get_span_context()
        record.trace_id = trace.format_trace_id(context.trace_id) if context.is_valid else "-"
        return True


def configure_logging(service: str) -> None:
    """One stdout format for api and worker; level from LOG_LEVEL (NFR-14)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(JobContextFilter())
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format=f"%(asctime)s %(levelname)s {service} [%(job_id)s] [%(trace_id)s] %(message)s",
        handlers=[handler],
    )
    # Uvicorn sets up its own handlers before loading the app; route its logs through ours.
    for name in ("uvicorn", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    # The SDK logs request bodies (document text) at DEBUG: keep them out even at LOG_LEVEL=DEBUG.
    logging.getLogger("openai").setLevel(logging.INFO)


class LogObserver(PipelineObserver):
    """Logs step boundaries and timings; SSE progress has its own observer in ProcessJob."""

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        start = time.monotonic()
        logger.info("Step %s started", name)
        try:
            yield
        except Exception as error:
            # Only the type: parser messages may quote document content.
            seconds = time.monotonic() - start
            logger.warning("Step %s failed in %.2fs: %s", name, seconds, type(error).__name__)
            raise
        logger.info("Step %s done in %.2fs", name, time.monotonic() - start)


class JobLog(JobObserver):
    """One summary line per job, never the form itself (NFR-06)."""

    def job_finished(self, result: JobResult, seconds: float) -> None:
        if result.error:
            logger.error("Job failed in %.1fs: %s", seconds, result.error)
            return
        # Shape set by ReportStep.
        report = result.result
        severities = Counter(issue["severity"] for issue in report["issues"])
        usage = report["usage"]
        logger.info(
            "Job done in %.1fs: confidence %.2f, %d ERROR, %d WARNING, tokens in %d out %d",
            seconds,
            report["confidence"]["overall"],
            severities["ERROR"],
            severities["WARNING"],
            usage["prompt_tokens"],
            usage["completion_tokens"],
        )
