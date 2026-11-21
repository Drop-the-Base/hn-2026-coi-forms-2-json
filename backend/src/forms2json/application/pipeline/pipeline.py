from collections.abc import Sequence
from typing import Any

from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.pipeline_observer import PipelineObserver


class Pipeline:
    """Runs steps in order, feeding each step's output to the next (ADR-0006)."""

    # Steps have different input/output types, so the chain is only typed per step.
    def __init__(self, steps: Sequence[PipelineStep[Any, Any]], observer: PipelineObserver) -> None:
        self._steps = steps
        self._observer = observer

    def run(self, data: object) -> object:
        for step in self._steps:
            with self._observer.step(step.name):
                data = step.run(data)
        return data
