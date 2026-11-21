import asyncio
import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Histogram, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    HistogramDataPoint,
    InMemoryMetricReader,
)

from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.adapters.outbound.observability.metrics import JobMetrics, MetricsObserver
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.ports.job_queue import Job, JobResult
from forms2json.application.use_cases.process_job import ProcessJob
from tests.unit.test_openai_compatible_client import SCHEMA, completion
from tests.unit.test_pipeline import Append, Boom
from tests.unit.test_process_job import Describe, FakeFileStore, FakeJobQueue

# Delta: each collect returns only what the test recorded since the previous one.
_reader = InMemoryMetricReader(preferred_temporality={Histogram: AggregationTemporality.DELTA})
# The global provider can be set only once per process; adapters' meters resolve to it lazily.
metrics.set_meter_provider(MeterProvider(metric_readers=[_reader]))


def _collect() -> dict[str, list[tuple[dict[str, Any], float, int]]]:
    """Metric name → (attributes, sum, count) of each histogram point since the last collect."""
    data = _reader.get_metrics_data()
    collected: dict[str, list[tuple[dict[str, Any], float, int]]] = {}
    for resource in data.resource_metrics if data else []:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                collected[metric.name] = [
                    (dict(point.attributes or {}), point.sum, point.count)
                    for point in metric.data.data_points
                    if isinstance(point, HistogramDataPoint)
                ]
    return collected


@pytest.fixture(autouse=True)
def _fresh_reader() -> Iterator[None]:
    _reader.get_metrics_data()
    yield


def test_step_duration_is_recorded_per_step_with_error_type_on_failure() -> None:
    with pytest.raises(ValueError):
        Pipeline([Append("a"), Boom()], MetricsObserver()).run("")

    points = _collect()["forms2json.pipeline.step.duration"]
    assert sorted([(attrs, count) for attrs, _, count in points], key=lambda p: p[0]["step"]) == [
        ({"step": "a"}, 1),
        ({"step": "boom", "error.type": "ValueError"}, 1),
    ]


def _job_result(prompt: int, completion: int, seconds: float, overall: float) -> Any:
    usage = {"prompt_tokens": prompt, "completion_tokens": completion, "seconds": seconds}
    return {"usage": usage, "confidence": {"overall": overall}}


def test_done_job_records_outcome_cost_from_rates_and_confidence() -> None:
    job_metrics = JobMetrics("m", cost_per_1k_tokens=2.0, cost_per_gpu_second=0.5)

    job_metrics.job_finished(JobResult(uuid.uuid4(), _job_result(1500, 500, 4.0, 0.9)), 7.0)

    collected = _collect()
    assert collected["forms2json.job.duration"] == [({"outcome": "done"}, 7.0, 1)]
    # 2000 tokens * 2.0 per 1k + 4 s * 0.5 per second
    assert collected["forms2json.job.cost"] == [({"gen_ai.request.model": "m"}, 6.0, 1)]
    assert collected["forms2json.job.confidence"] == [({}, 0.9, 1)]


def test_failed_job_records_outcome_and_error_type_only() -> None:
    JobMetrics("m", 1.0, 1.0).job_finished(JobResult(uuid.uuid4(), error="LlmCallFailed"), 3.0)

    collected = _collect()
    assert collected["forms2json.job.duration"] == [
        ({"outcome": "failed", "error.type": "LlmCallFailed"}, 3.0, 1)
    ]
    assert collected.get("forms2json.job.cost", []) == []


def test_process_job_reports_finished_job_to_its_observer() -> None:
    files, queue = FakeFileStore(), FakeJobQueue()
    job = Job(uuid.uuid4(), "application/pdf")  # no file saved, so the job fails
    use_case = ProcessJob(
        files, lambda progress: Pipeline([Describe()], progress), queue, JobMetrics("m", 0, 0)
    )

    asyncio.run(use_case.execute(job))

    ((attrs, _, count),) = _collect()["forms2json.job.duration"]
    assert (attrs, count) == ({"outcome": "failed", "error.type": "KeyError"}, 1)


def test_llm_call_records_input_and_output_tokens_with_model() -> None:
    http_client = httpx2.Client(
        transport=httpx2.MockTransport(lambda _: completion('{"title": "ok"}'))
    )
    OpenAiCompatibleLlmClient("http://llm/v1", "m", 5.0, 100, http_client).generate_json(
        "system", "user", SCHEMA
    )

    common = {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "openai",
        "gen_ai.request.model": "m",
    }
    assert sorted(_collect()["gen_ai.client.token.usage"], key=lambda p: p[1]) == [
        ({**common, "gen_ai.token.type": "output"}, 5, 1),
        ({**common, "gen_ai.token.type": "input"}, 10, 1),
    ]
