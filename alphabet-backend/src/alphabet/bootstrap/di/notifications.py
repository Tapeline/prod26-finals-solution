from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide, provide_all

from alphabet.notifications.application.interactors import (
    CreateNotificationRule,
    DeleteNotificationRule,
    PublishNotification,
    ReadAllNotificationRule,
    ReadNotificationRule,
    SelectAndSend,
    UpdateNotificationRule,
)
from alphabet.notifications.application.interfaces import (
    GroupedNotificationBuilder,
    NotificationChannelFactory,
    NotificationCooldownStore,
    NotificationRuleRepository,
    PreparedNotificationQueue,
)
from alphabet.notifications.infrastructure.channels.factory import (
    DefaultNotificationChannelFactory,
)
from alphabet.notifications.infrastructure.repo import (
    SqlNotificationRuleRepository,
    SqlPreparedNotificationQueue,
)
from alphabet.notifications.infrastructure.templating import (
    JinjaGroupedNotificationBuilder,
)
from alphabet.notifications.infrastructure.valkey import (
    ValkeyNotificationCooldownStore,
)
from alphabet.shared.config import Config


class NotificationsInteractorsDIProvider(Provider):
    interactors = provide_all(
        CreateNotificationRule,
        DeleteNotificationRule,
        ReadAllNotificationRule,
        ReadNotificationRule,
        UpdateNotificationRule,
        PublishNotification,
        scope=Scope.REQUEST,
    )


class NotificationsWorkerDIProvider(Provider):
    interactors = provide_all(
        SelectAndSend,
        scope=Scope.REQUEST,
    )
    valkey_cooldowns = provide(
        ValkeyNotificationCooldownStore,
        provides=NotificationCooldownStore,
        scope=Scope.REQUEST,
    )
    jinja_templater = provide(
        JinjaGroupedNotificationBuilder,
        provides=GroupedNotificationBuilder,
        scope=Scope.APP,
    )

    @provide(scope=Scope.APP)
    async def provide_factory(
        self,
        config: Config,
    ) -> AsyncIterable[NotificationChannelFactory]:
        factory = DefaultNotificationChannelFactory(config)
        yield factory
        await factory.close()


class NotificationPublisherDIProvider(Provider):
    publisher = provide(
        PublishNotification,
        scope=Scope.REQUEST,
    )
    rule_repo = provide(
        SqlNotificationRuleRepository,
        provides=NotificationRuleRepository,
        scope=Scope.REQUEST,
    )
    notif_buffer = provide(
        SqlPreparedNotificationQueue,
        provides=PreparedNotificationQueue,
        scope=Scope.REQUEST,
    )


def get_notifications_providers() -> list[Provider]:
    return [
        NotificationsInteractorsDIProvider(),
        NotificationsWorkerDIProvider(),
        NotificationPublisherDIProvider(),
    ]
