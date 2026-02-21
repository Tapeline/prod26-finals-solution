from email.message import EmailMessage
from typing import final, override

import aiosmtplib

from alphabet.notifications.application.interfaces import NotificationChannel
from alphabet.shared.config import SmtpConfig


@final
class EmailNotificationChannel(NotificationChannel):
    def __init__(self, recipient_email: str, config: SmtpConfig) -> None:
        self.recipient = recipient_email
        self.config = config

    @override
    async def send(self, message: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.config.sender_email
        msg["To"] = self.recipient
        msg["Subject"] = self.config.subject
        msg.set_content(message)
        auth_kwargs = {}
        if self.config.username and self.config.password:
            auth_kwargs["username"] = self.config.username
            auth_kwargs["password"] = self.config.password
        await aiosmtplib.send(
            msg,
            hostname=self.config.host,
            port=self.config.port,
            use_tls=self.config.use_tls,
            **auth_kwargs,  # type: ignore[arg-type]
        )
