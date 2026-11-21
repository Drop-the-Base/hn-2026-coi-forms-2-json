"""Worker process: python -m forms2json.adapters.inbound.worker"""

import asyncio
import logging

from forms2json.adapters.inbound.worker.consumer import run_worker
from forms2json.bootstrap import build_worker
from forms2json.config import get_settings


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    queue, process_job = await build_worker(get_settings())
    try:
        await run_worker(queue, process_job)
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(main())
