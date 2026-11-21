import asyncio

from forms2json.application.ports.job_queue import JobQueue
from forms2json.application.use_cases.process_job import ProcessJob


async def run_worker(queue: JobQueue, process_job: ProcessJob) -> None:
    """Feeds queued jobs to ProcessJob until the process is stopped."""
    await queue.consume_jobs(process_job.execute)
    await asyncio.Future()  # consumption runs in aio-pika callbacks; just keep the loop alive
