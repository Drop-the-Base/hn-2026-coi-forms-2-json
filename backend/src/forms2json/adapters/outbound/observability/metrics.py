import time
from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import metrics

from forms2json.application.ports.job_observer import JobObserver
from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.pipeline_observer import PipelineObserver

_meter = metrics.get_meter(__name__)
# Steps and jobs take from milliseconds (ingest) to minutes (LLM on CPU).
_SECONDS = [0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600]
_step_duration = _meter.create_histogram(
    "forms2json.pipeline.step.duration", unit="s", explicit_bucket_boundaries_advisory=_SECONDS
)
# Its count by `outcome` is the done/failed job counter.
_job_duration = _meter.create_histogram(
    "forms2json.job.duration", unit="s", explicit_bucket_boundaries_advisory=_SECONDS
)
_job_cost = _meter.create_histogram(
    "forms2json.job.cost",
    unit="{cost}",
    description="From COST_PER_1K_TOKENS and COST_PER_GPU_SECOND",
)
_job_confidence = _meter.create_histogram(
    "forms2json.job.confidence",
    unit="1",
    explicit_bucket_boundaries_advisory=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95],
)


class MetricsObserver(PipelineObserver):
    """Step latency; a failed step carries `error.type` (NFR-14)."""

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        start = time.monotonic()
        attributes = {"step": name}
        try:
            yield
        except Exception as error:
            attributes["error.type"] = type(error).__name__
            raise
        finally:
            _step_duration.record(time.monotonic() - start, attributes)


class JobMetrics(JobObserver):
    """Job latency and outcome; for done jobs also cost and overall confidence (NFR-13)."""

    def __init__(self, model: str, cost_per_1k_tokens: float, cost_per_gpu_second: float) -> None:
        self._model = model
        self._cost_per_1k_tokens = cost_per_1k_tokens
        self._cost_per_gpu_second = cost_per_gpu_second

    def job_finished(self, result: JobResult, seconds: float) -> None:
        if result.error:
            _job_duration.record(seconds, {"outcome": "failed", "error.type": result.error})
            return
        _job_duration.record(seconds, {"outcome": "done"})
        # Shape set by ReportStep. Local models cost compute time, not an invoice (architecture §7).
        usage = result.result["usage"]
        tokens = usage["prompt_tokens"] + usage["completion_tokens"]
        cost = (
            tokens / 1000 * self._cost_per_1k_tokens + usage["seconds"] * self._cost_per_gpu_second
        )
        _job_cost.record(cost, {"gen_ai.request.model": self._model})
        _job_confidence.record(result.result["confidence"]["overall"])
