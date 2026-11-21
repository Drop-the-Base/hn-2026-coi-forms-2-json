import asyncio
from uuid import UUID

from forms2json.application.ports.job_queue import JobResult
from forms2json.application.ports.result_store import ResultStore

POLL_INTERVAL_SECONDS = 0.2


class GetJobResult:
    def __init__(self, results: ResultStore) -> None:
        self._results = results

    def execute(self, job_id: UUID) -> JobResult | None:
        """None while pending; raises UnknownJob for an unknown or expired job."""
        return self._results.get(job_id)

    async def wait(self, job_id: UUID, timeout_seconds: float) -> JobResult | None:
        """Like execute, but waits up to timeout_seconds for the result (FR-06)."""
        # shortcut: polls the store every 0.2 s, use an asyncio.Event per job if it shows in load.
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while (result := self.execute(job_id)) is None:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return None
            await asyncio.sleep(min(POLL_INTERVAL_SECONDS, remaining))
        return result
