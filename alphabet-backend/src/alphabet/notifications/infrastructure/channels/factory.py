from typing import final, override

from aiogram import Bot
from structlog import getLogger

from alphabet.notifications.application.interfaces import (
    NotificationChannel,
    NotificationChannelFactory,
)
from alphabet.notifications.domain.notifications import ConnectionString
from alphabet.notifications.infrastructure.channels.smtp import (
    EmailNotificationChannel,
)
from alphabet.notifications.infrastructure.channels.telegram import (
    TelegramNotificationChannel,
)
from alphabet.shared.commons import autoinit
from alphabet.shared.config import Config

logger = getLogger(__name__)


@autoinit
@final
class DefaultNotificationChannelFactory(NotificationChannelFactory):
    config: Config
    bot: Bot | None = None

    def __post_init__(self) -> None:
        if self.config.notifications.telegram.is_set_up:
            self.bot = Bot(token=self.config.notifications.telegram.token)
        else:
            self.bot = None

    async def close(self) -> None:
        if self.bot:
            await self.bot.session.close()

    @override
    def create(self, connection: ConnectionString) -> NotificationChannel:
        match connection.integration:
            case "email":
                if not self.config.notifications.smtp.is_set_up:
                    logger.error(
                        "Used email channel, but not configured one",
                        connection=connection,
                    )
                    return FallbackNotificationChannel()
                return EmailNotificationChannel(
                    recipient_email=connection.resource,
                    config=self.config.notifications.smtp,
                )
            case "tg":
                if not self.bot:
                    logger.error(
                        "Used telegram channel, but not configured one",
                        connection=connection,
                    )
                    return FallbackNotificationChannel()
                return TelegramNotificationChannel(
                    chat_id=connection.resource,
                    bot=self.bot,
                )
            case _:
                logger.error(
                    "Used unsupported channel type",
                    connection=connection,
                )
                return FallbackNotificationChannel()


@final
class FallbackNotificationChannel(NotificationChannel):
    @override
    async def send(self, message: str) -> None:
        logger.warning(
            "Notification lost due to fallback",
            message_preview=message[:100],
        )
