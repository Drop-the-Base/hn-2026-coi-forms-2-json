import asyncio
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import httpx2
import pytest
from aio_pika import Message
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractIncomingMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.adapters.outbound.observability.tracing_observer import TracingObserver
from forms2json.adapters.outbound.queue.rabbitmq_job_queue import (
    RabbitMqJobQueue,
    _handle_in_trace,
)
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.ports.job_queue import Job
from tests.unit.test_openai_compatible_client import SCHEMA, completion
from tests.unit.test_pipeline import Append, Boom

_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
# The global provider can be set only once per process; adapters' tracers resolve to it lazily.
trace.set_tracer_provider(_provider)
_tracer = trace.get_tracer(__name__)


@pytest.fixture(autouse=True)
def spans() -> Iterator[InMemorySpanExporter]:
    _exporter.clear()
    yield _exporter


def test_step_spans_are_children_of_the_job_span_and_failure_is_an_error(
    spans: InMemorySpanExporter,
) -> None:
    with _tracer.start_as_current_span("job") as job, pytest.raises(ValueError):
        Pipeline([Append("a"), Boom()], TracingObserver()).run("")

    by_name = {span.name: span for span in spans.get_finished_spans()}
    assert set(by_name) == {"job", "step a", "step boom"}
    for name in ("step a", "step boom"):
        parent = by_name[name].parent
        assert parent is not None
        assert parent.span_id == job.get_span_context().span_id
    assert by_name["step a"].status.status_code is StatusCode.UNSET
    assert by_name["step boom"].status.status_code is StatusCode.ERROR


class _CapturingExchange:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    async def publish(self, message: Message, routing_key: str) -> None:
        self.messages.append(message)


def test_trace_context_travels_in_message_headers(spans: InMemorySpanExporter) -> None:
    exchange = _CapturingExchange()
    channel = cast(AbstractChannel, SimpleNamespace(default_exchange=exchange))
    queue = RabbitMqJobQueue(cast(Any, None), channel, cast(AbstractExchange, exchange))
    seen_trace_ids: list[int] = []

    async def handler(job: Job) -> None:
        seen_trace_ids.append(trace.get_current_span().get_span_context().trace_id)

    async def scenario() -> int:
        job = Job(uuid4(), "application/pdf")
        with _tracer.start_as_current_span("POST /jobs") as request:
            await queue.publish_job(job)
        sent = exchange.messages[0]
        incoming = SimpleNamespace(headers=sent.headers, exchange="", routing_key="jobs")
        await _handle_in_trace(cast(AbstractIncomingMessage, incoming), job, handler)
        return request.get_span_context().trace_id

    request_trace_id = asyncio.run(scenario())

    assert seen_trace_ids == [request_trace_id]
    consumer = next(s for s in spans.get_finished_spans() if s.name == "process jobs")
    assert consumer.kind is trace.SpanKind.CONSUMER


def test_message_without_trace_context_gets_no_span(spans: InMemorySpanExporter) -> None:
    handled: list[object] = []

    async def handler(item: object) -> None:
        handled.append(item)

    incoming = SimpleNamespace(headers={}, exchange="progress", routing_key="x")
    asyncio.run(_handle_in_trace(cast(AbstractIncomingMessage, incoming), "event", handler))

    assert handled == ["event"]
    assert spans.get_finished_spans() == ()


def test_llm_call_span_has_gen_ai_usage(spans: InMemorySpanExporter) -> None:
    http_client = httpx2.Client(
        transport=httpx2.MockTransport(lambda _: completion('{"title": "ok"}'))
    )
    client = OpenAiCompatibleLlmClient("http://llm/v1", "m", 5.0, 100, http_client)

    client.generate_json("system", "user", SCHEMA)

    (span,) = spans.get_finished_spans()
    assert span.name == "chat m"
    assert span.attributes == {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "openai",
        "gen_ai.request.model": "m",
        "gen_ai.usage.input_tokens": 10,
        "gen_ai.usage.output_tokens": 5,
    }
