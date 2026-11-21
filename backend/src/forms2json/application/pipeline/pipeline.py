from collections.abc import Sequence
from typing import Any

from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.pipeline_observer import PipelineObserver


class Pipeline:
    """Runs steps in order, feeding each step's output to the next (ADR-0006)."""

    # Steps have different input/output types, so the chain is only typed per step.
    def __init__(self, steps: Sequence[PipelineStep[Any, Any]]) -> None:
        self._steps = steps

    def run(self, data: object, observer: PipelineObserver) -> object:
        """The observer comes per run, because progress events belong to one job."""
        for step in self._steps:
            with observer.step(step.name):
                data = step.run(data)
        return data
