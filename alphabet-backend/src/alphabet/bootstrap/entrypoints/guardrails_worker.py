import asyncio
import signal
import sys

from dishka import AsyncContainer, make_async_container
from structlog import getLogger

from alphabet.bootstrap.config import service_config_loader
from alphabet.bootstrap.di.decisions import (
    DecisionsCacheSyncsDIProvider,
)
from alphabet.bootstrap.di.experiments import (
    ExperimentRepoDIProvider,
)
from alphabet.bootstrap.di.guardrails import (
    GuardrailWorkerDIProvider, GuardrailsStorageDIProvider,
)
from alphabet.bootstrap.di.metrics import (
    MetricsStorageDIProvider,
)
from alphabet.bootstrap.di.notifications import NotificationPublisherDIProvider
from alphabet.bootstrap.di.shared import (
    ClickHouseDIProvider,
    ConfigDIProvider,
    MessageQueueErsatzDIProvider,
    SqlTransactionDIProvider,
    TimeDIProvider,
    ValkeyDIProvider,
)
from alphabet.bootstrap.logging import configure_structlog
from alphabet.guardrails.infrastructure.worker import GuardrailWorker
from alphabet.shared.config import Config


def _create_container(config: Config) -> AsyncContainer:
    return make_async_container(
        MessageQueueErsatzDIProvider(),
        DecisionsCacheSyncsDIProvider(),
        ConfigDIProvider(),
        SqlTransactionDIProvider(),
        ClickHouseDIProvider(),
        TimeDIProvider(),
        ValkeyDIProvider(),
        ExperimentRepoDIProvider(),
        MetricsStorageDIProvider(),
        GuardrailsStorageDIProvider(),
        GuardrailWorkerDIProvider(),
        NotificationPublisherDIProvider(),
        context={
            Config: config,
        },
    )


async def run_worker() -> None:
    config = service_config_loader.load()
    container = _create_container(config)
    configure_structlog(use_json=config.logging.use_json)

    logger = getLogger(__name__)
    logger.info("Starting guardrails worker process")

    worker = GuardrailWorker(container, config.workers)

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
        try:  # noqa: SIM105
            await worker_task
        except asyncio.CancelledError:
            pass
    finally:
        logger.info("Cleaning up")
        await container.close()


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
