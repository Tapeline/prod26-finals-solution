import asyncio
from typing import final

from dishka import AsyncContainer
from structlog import getLogger

from alphabet.notifications.application.interactors import SelectAndSend
from alphabet.shared.config import WorkersConfig


@final
class NotificationWorker:
    def __init__(
        self,
        container: AsyncContainer,
        config: WorkersConfig,
    ) -> None:
        self.container = container
        self.is_running = False
        self.logger = getLogger("notification-worker")
        self.interval = config.notification_interval_s

    async def start(self) -> None:
        self.is_running = True
        self.logger.info("Notification worker started")
        while self.is_running:
            try:
                await self._run_cycle()
            except Exception as exc:
                self.logger.exception(
                    "Notification worker cycle failed",
                    exc_info=exc,
                )
            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        self.is_running = False

    async def _run_cycle(self) -> None:
        async with self.container() as nested:
            interactor = await nested.get(SelectAndSend)
            await interactor()
