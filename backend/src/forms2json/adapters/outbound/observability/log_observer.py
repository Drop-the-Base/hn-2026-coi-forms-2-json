import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from forms2json.application.ports.pipeline_observer import PipelineObserver

logger = logging.getLogger(__name__)


class LogObserver(PipelineObserver):
    """Logs step boundaries and timings; OTel spans and SSE progress come with ADR-0014."""

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        start = time.monotonic()
        logger.info("Step %s started", name)
        yield
        logger.info("Step %s done in %.2fs", name, time.monotonic() - start)
