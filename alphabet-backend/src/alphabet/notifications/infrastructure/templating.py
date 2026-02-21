from typing import final, override

from jinja2 import BaseLoader, Environment

from alphabet.notifications.application.interfaces import \
    GroupedNotificationBuilder
from alphabet.notifications.domain.notifications import (
    PreparedNotification,
)


@final
class JinjaGroupedNotificationBuilder(GroupedNotificationBuilder):
    def __init__(self) -> None:
        self.env = Environment(loader=BaseLoader(), autoescape=True)

    @override
    def render_merge(
        self, template: str, notifications: list[PreparedNotification]
    ) -> str:
        jinja_template = self.env.from_string(template)
        return "\n===\n".join(
            jinja_template.render(
                notification=notification,
                **notification.meta
            )
            for notification in notifications
        )
