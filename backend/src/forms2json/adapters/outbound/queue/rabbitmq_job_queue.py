import logging
from collections.abc import Awaitable, Callable
from typing import Self

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractRobustConnection,
    HeadersType,
)
from opentelemetry import propagate, trace
from pydantic import TypeAdapter, ValidationError

from forms2json.application.ports.job_queue import Job, JobQueue, JobResult, ProgressEvent

JOBS = "jobs"
RESULTS = "results"
PROGRESS = "progress"  # topic exchange, routing key = job_id (ADR-0014)

_job = TypeAdapter(Job)
_result = TypeAdapter(JobResult)
_progress = TypeAdapter(ProgressEvent)

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


class RabbitMqJobQueue(JobQueue):
    """Nothing survives a broker restart: non-durable queues, transient messages (NFR-06)."""

    def __init__(
        self,
        connection: AbstractRobustConnection,
        channel: AbstractChannel,
        progress: AbstractExchange,
    ) -> None:
        self._connection = connection
        self._channel = channel
        self._progress = progress

    @classmethod
    async def connect(cls, url: str) -> Self:
        connection = await aio_pika.connect_robust(url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)  # one job per worker at a time; others wait
        for name in (JOBS, RESULTS):
            await channel.declare_queue(name, durable=False)
        progress = await channel.declare_exchange(PROGRESS, ExchangeType.TOPIC, durable=False)
        return cls(connection, channel, progress)

    async def close(self) -> None:
        await self._connection.close()

    async def publish_job(self, job: Job) -> None:
        await self._publish(self._channel.default_exchange, JOBS, _job.dump_json(job))

    async def consume_jobs(self, handler: Callable[[Job], Awaitable[None]]) -> None:
        await self._consume(JOBS, _job, handler)

    async def publish_result(self, result: JobResult) -> None:
        await self._publish(self._channel.default_exchange, RESULTS, _result.dump_json(result))

    async def consume_results(self, handler: Callable[[JobResult], Awaitable[None]]) -> None:
        # shortcut: one api replica consumes all results; replicas would split them between
        # themselves, so switch to a fanout exchange or a shared store when scaling the api.
        await self._consume(RESULTS, _result, handler)

    async def publish_progress(self, event: ProgressEvent) -> None:
        await self._publish(self._progress, str(event.job_id), _progress.dump_json(event))

    async def consume_progress(self, handler: Callable[[ProgressEvent], Awaitable[None]]) -> None:
        # Each api replica gets its own queue with every job's progress; it dies with the replica.
        queue = await self._channel.declare_queue(exclusive=True, auto_delete=True)
        await queue.bind(self._progress, routing_key="#")
        await self._consume(queue.name, _progress, handler)

    async def _consume[T](
        self, queue_name: str, schema: TypeAdapter[T], handler: Callable[[T], Awaitable[None]]
    ) -> None:
        async def on_message(message: AbstractIncomingMessage) -> None:
            # Acked after the handler, so a consumer killed mid-message leaves it for another one.
            async with message.process():
                try:
                    item = schema.validate_json(message.body)
                except ValidationError:
                    logger.warning(
                        "Dropping malformed %s message %s", queue_name, message.message_id
                    )
                    return
                await _handle_in_trace(message, item, handler)

        queue = await self._channel.get_queue(queue_name)
        await queue.consume(on_message)

    async def _publish(self, exchange: AbstractExchange, routing_key: str, body: bytes) -> None:
        headers: HeadersType = {}
        propagate.inject(headers)  # traceparent: the worker continues the api's trace (NFR-14)
        message = Message(
            body,
            content_type="application/json",
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
            headers=headers,
        )
        await exchange.publish(message, routing_key=routing_key)


async def _handle_in_trace[T](
    message: AbstractIncomingMessage, item: T, handler: Callable[[T], Awaitable[None]]
) -> None:
    context = propagate.extract(message.headers)
    if not trace.get_current_span(context).get_span_context().is_valid:
        # Progress events from the pipeline thread carry no trace; a root trace each is noise.
        await handler(item)
        return
    destination = message.exchange or message.routing_key  # "jobs", "results" or "progress"
    with _tracer.start_as_current_span(
        f"process {destination}", context=context, kind=trace.SpanKind.CONSUMER
    ):
        await handler(item)
