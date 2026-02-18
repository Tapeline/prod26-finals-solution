import asyncio
import signal
import sys

from clickhouse_connect.driver import AsyncClient
from clickhouse_connect import get_async_client

from alphabet.bootstrap.config import service_config_loader
from alphabet.bootstrap.logging import configure_structlog
from alphabet.shared.config import Config
from alphabet.subject_events.infrastructure.click.attribution_worker import (
    AttributionWorker,
)


async def run_worker() -> None:
    config = service_config_loader.load()
    
    configure_structlog(use_json=config.logging.use_json)
    
    clickhouse_client = await get_async_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        database=config.clickhouse.database,
        username=config.clickhouse.username,
        password=config.clickhouse.password,
    )
    
    worker = AttributionWorker(clickhouse_client)

    # thanks cursor for this suggestion
    shutdown_event = asyncio.Event()
    
    def signal_handler() -> None:
        shutdown_event.set()

    # some windows style crap i needed to fix
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    
    try:
        worker_task = asyncio.create_task(worker.start())
        await shutdown_event.wait()
        await worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    finally:
        await clickhouse_client.close()


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
