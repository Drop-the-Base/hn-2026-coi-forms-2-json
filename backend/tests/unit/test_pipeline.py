from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.pipeline_observer import PipelineObserver


class FakeObserver(PipelineObserver):
    def __init__(self) -> None:
        self.events: list[str] = []

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        self.events.append(f"started {name}")
        try:
            yield
        except Exception:
            self.events.append(f"failed {name}")
            raise
        self.events.append(f"done {name}")


class Append(PipelineStep[str, str]):
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, data: str) -> str:
        return data + self.name


class Boom(PipelineStep[str, str]):
    name = "boom"

    def run(self, data: str) -> str:
        raise ValueError(data)


def test_steps_run_in_order_and_observer_sees_each_boundary() -> None:
    observer = FakeObserver()

    result = Pipeline([Append("a"), Append("b")], observer).run("")

    assert result == "ab"
    assert observer.events == ["started a", "done a", "started b", "done b"]


def test_failing_step_stops_pipeline_and_is_reported() -> None:
    observer = FakeObserver()

    with pytest.raises(ValueError):
        Pipeline([Append("a"), Boom(), Append("c")], observer).run("")

    assert observer.events == ["started a", "done a", "started boom", "failed boom"]
