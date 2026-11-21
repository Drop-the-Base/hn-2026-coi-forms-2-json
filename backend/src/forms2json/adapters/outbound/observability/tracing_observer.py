from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace

from forms2json.application.ports.pipeline_observer import PipelineObserver

_tracer = trace.get_tracer(__name__)


class TracingObserver(PipelineObserver):
    """One OTel span per pipeline step; an exception marks it as an error (NFR-14)."""

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        with _tracer.start_as_current_span(f"step {name}"):
            yield
