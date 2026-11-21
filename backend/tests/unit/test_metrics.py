import asyncio
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import httpx2
import pytest
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Histogram, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    HistogramDataPoint,
    InMemoryMetricReader,
    NumberDataPoint,
)

from forms2json.adapters.outbound.llm.openai_compatible_client import (
    MAX_ATTEMPTS,
    OpenAiCompatibleLlmClient,
)
from forms2json.adapters.outbound.observability.metrics import JobMetrics, MetricsObserver
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.ports.job_queue import Job, JobResult
from forms2json.application.ports.llm_client import LlmCallFailed
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.domain.cost import CostRates
from tests.unit.test_openai_compatible_client import SCHEMA, completion
from tests.unit.test_pipeline import Append, Boom
from tests.unit.test_process_job import Describe, FakeFileStore, FakeJobQueue

# Delta: each collect returns only what the test recorded since the previous one.
_reader = InMemoryMetricReader(
    preferred_temporality={
        Histogram: AggregationTemporality.DELTA,
        Counter: AggregationTemporality.DELTA,
    }
)
# The global provider can be set only once per process; adapters' meters resolve to it lazily.
metrics.set_meter_provider(MeterProvider(metric_readers=[_reader]))


def _collect() -> dict[str, list[tuple[dict[str, Any], float, int]]]:
    """Metric name → (attributes, sum, count) of each point since the last collect.

    A counter point has its value as the sum and count 1.
    """
    data = _reader.get_metrics_data()
    collected: dict[str, list[tuple[dict[str, Any], float, int]]] = {}
    for resource in data.resource_metrics if data else []:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                collected[metric.name] = [
                    (dict(point.attributes or {}), point.sum, point.count)
                    if isinstance(point, HistogramDataPoint)
                    else (dict(point.attributes or {}), point.value, 1)
                    for point in metric.data.data_points
                    if isinstance(point, HistogramDataPoint | NumberDataPoint)
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


def test_done_job_records_outcome_cost_from_result_and_confidence() -> None:
    result = {"usage": {"cost": 6.0}, "confidence": {"overall": 0.9}}

    JobMetrics("m").job_finished(JobResult(uuid.uuid4(), result), 7.0)

    collected = _collect()
    assert collected["forms2json.job.duration"] == [({"outcome": "done"}, 7.0, 1)]
    assert collected["forms2json.job.cost"] == [({"gen_ai.request.model": "m"}, 6.0, 1)]
    assert collected["forms2json.job.confidence"] == [({}, 0.9, 1)]


def test_failed_job_records_outcome_and_error_type_only() -> None:
    JobMetrics("m").job_finished(JobResult(uuid.uuid4(), error="LlmCallFailed"), 3.0)

    collected = _collect()
    assert collected["forms2json.job.duration"] == [
        ({"outcome": "failed", "error.type": "LlmCallFailed"}, 3.0, 1)
    ]
    assert collected.get("forms2json.job.cost", []) == []


def test_process_job_reports_finished_job_to_its_observer() -> None:
    files, queue = FakeFileStore(), FakeJobQueue()
    job = Job(uuid.uuid4(), "application/pdf")  # no file saved, so the job fails
    use_case = ProcessJob(
        files, lambda progress: Pipeline([Describe()], progress), queue, [JobMetrics("m")]
    )

    asyncio.run(use_case.execute(job))

    ((attrs, _, count),) = _collect()["forms2json.job.duration"]
    assert (attrs, count) == ({"outcome": "failed", "error.type": "KeyError"}, 1)


def test_llm_call_records_input_and_output_tokens_with_model() -> None:
    http_client = httpx2.Client(
        transport=httpx2.MockTransport(lambda _: completion('{"title": "ok"}'))
    )
    rates = CostRates(per_1m_input_tokens=1_000_000, per_1m_output_tokens=3_000_000)
    OpenAiCompatibleLlmClient(
        "http://llm/v1", "m", 5.0, 100, http_client, cost_rates=rates
    ).generate_json("system", "user", SCHEMA)

    common = {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "openai",
        "gen_ai.request.model": "m",
    }
    collected = _collect()
    assert sorted(collected["gen_ai.client.token.usage"], key=lambda p: p[1]) == [
        ({**common, "gen_ai.token.type": "output"}, 5, 1),
        ({**common, "gen_ai.token.type": "input"}, 10, 1),
    ]
    # 10 input tokens at 1 per token, 5 output tokens at 3 per token
    assert sorted(collected["forms2json.llm.call.cost"], key=lambda p: p[1]) == [
        ({**common, "gen_ai.token.type": "input"}, 10.0, 1),
        ({**common, "gen_ai.token.type": "output"}, 15.0, 1),
    ]


def _timeout(request: httpx2.Request) -> httpx2.Response:
    raise httpx2.ReadTimeout("slow model", request=request)


@pytest.mark.parametrize(
    ("handler", "error_type", "attempts"),
    [
        (lambda _: httpx2.Response(429, json={"error": "limit"}), "429", 1),
        (_timeout, "APITimeoutError", MAX_ATTEMPTS),
    ],
)
def test_llm_errors_are_counted_by_type(
    handler: Callable[[httpx2.Request], httpx2.Response], error_type: str, attempts: int
) -> None:
    http_client = httpx2.Client(transport=httpx2.MockTransport(handler))
    with pytest.raises(LlmCallFailed):
        OpenAiCompatibleLlmClient("http://llm/v1", "m", 5.0, 100, http_client).generate_json(
            "system", "user", SCHEMA
        )

    assert _collect()["forms2json.llm.errors"] == [
        ({"gen_ai.request.model": "m", "error.type": error_type}, attempts, 1)
    ]
