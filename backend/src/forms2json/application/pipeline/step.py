from abc import ABC, abstractmethod


class PipelineStep[In, Out](ABC):
    name: str

    @abstractmethod
    def run(self, data: In) -> Out: ...
