from typing import final, override

from aiogram import Bot
from structlog import getLogger

from alphabet.notifications.application.interfaces import NotificationChannel

logger = getLogger(__name__)


@final
class TelegramNotificationChannel(NotificationChannel):
    def __init__(self, chat_id: str, bot: Bot) -> None:
        self.chat_id = chat_id
        self.bot = bot

    @override
    async def send(self, message: str) -> None:
        parts = 0
        logger.info("Sending message", to=self.chat_id)
        while message:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
            )
            message = message[4096:]
            parts += 1
            # Telegram has a limit, alas
        if parts > 1:
            logger.info("Sent tg split into parts", parts=parts)
