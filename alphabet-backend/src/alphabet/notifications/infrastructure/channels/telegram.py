from typing import final, override

from aiogram import Bot

from alphabet.notifications.application.interfaces import NotificationChannel


@final
class TelegramNotificationChannel(NotificationChannel):
    def __init__(self, chat_id: str, bot: Bot) -> None:
        self.chat_id = chat_id
        self.bot = bot

    @override
    async def send(self, message: str) -> None:
        while message:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
            )
            message = message[4096:]
            # Telegram has a limit, alas
