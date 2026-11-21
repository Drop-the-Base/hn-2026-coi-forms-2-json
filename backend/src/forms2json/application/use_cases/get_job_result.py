from uuid import UUID

from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.result_store import ResultStore


class GetJobResult:
    def __init__(self, results: ResultStore) -> None:
        self._results = results

    def execute(self, job_id: UUID) -> JobResult | None:
        """None while pending; raises UnknownJob for an unknown or expired job."""
        return self._results.get(job_id)
