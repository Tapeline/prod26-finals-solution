from abc import abstractmethod
from collections.abc import Collection
from typing import Protocol

from alphabet.notifications.domain.notifications import (
    ConnectionString,
    Fingerprint,
    NotificationRule,
    NotificationRuleId,
    PreparedNotification,
)
from alphabet.shared.application.pagination import Pagination


class NotificationRuleRepository(Protocol):
    @abstractmethod
    async def create(self, rule: NotificationRule) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, rule: NotificationRule) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        rule_id: NotificationRuleId,
    ) -> NotificationRule | None:
        raise NotImplementedError

    @abstractmethod
    async def all(
        self,
        pagination: Pagination | None,
    ) -> list[NotificationRule]:
        raise NotImplementedError

    # questionable, but needed for performance
    @abstractmethod
    async def all_of_trigger_type(
        self,
        trigger_type: str,
    ) -> list[NotificationRule]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, rule_id: NotificationRuleId) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_ids(
        self,
        ids: list[NotificationRuleId],
    ) -> list[NotificationRule]:
        raise NotImplementedError


class PreparedNotificationQueue(Protocol):
    @abstractmethod
    async def push_all(
        self,
        notifications: list[PreparedNotification],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def all(self) -> list[PreparedNotification]:
        raise NotImplementedError

    @abstractmethod
    async def pop_all(self, fingerprints: list[Fingerprint]) -> None:
        raise NotImplementedError


class NotificationChannel(Protocol):
    @abstractmethod
    async def send(self, message: str) -> None:
        raise NotImplementedError


class NotificationChannelFactory(Protocol):
    @abstractmethod
    def create(self, connection: ConnectionString) -> NotificationChannel:
        raise NotImplementedError


class GroupedNotificationBuilder(Protocol):
    @abstractmethod
    def render_merge(
        self,
        template: str,
        notifications: list[PreparedNotification],
    ) -> str:
        raise NotImplementedError


class NotificationCooldownStore(Protocol):
    @abstractmethod
    async def filter_in_cooldown(
        self,
        rule_ids: Collection[NotificationRuleId],
    ) -> set[NotificationRuleId]:
        raise NotImplementedError

    @abstractmethod
    async def place_cooldowns(
        self,
        cooldowns_s: dict[NotificationRuleId, int],
    ) -> None:
        raise NotImplementedError
