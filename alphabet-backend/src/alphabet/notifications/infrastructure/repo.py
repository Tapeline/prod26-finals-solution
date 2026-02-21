from typing import Any, cast, override, assert_never

from sqlalchemy import (
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Row
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.guardrails.domain import GuardRuleId
from alphabet.notifications.application.interfaces import (
    NotificationRuleRepository, PreparedNotificationQueue,
)
from alphabet.notifications.domain.notifications import (
    AnyExperimentTrigger,
    ConnectionString,
    ExperimentTrigger,
    Fingerprint,
    GuardrailTrigger,
    NotificationRule,
    NotificationRuleId,
    PreparedNotification,
    Ratelimit,
    Trigger,
)
from alphabet.notifications.infrastructure.tables import (
    notification_rules,
    prepared_notifications,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


class SqlNotificationRuleRepository(NotificationRuleRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def create(self, rule: NotificationRule) -> None:
        t_type, t_resource = _serialize_trigger(rule.trigger)
        await self.session.execute(
            insert(notification_rules).values(
                id=rule.id,
                trigger_type=t_type,
                trigger_resource=t_resource,
                connection_string=(
                    f"{rule.connection.integration}://"
                    f"{rule.connection.resource}"
                ),
                message_template=rule.message_template,
                rate_limit_s=rule.rate_limit.seconds,
            )
        )

    @override
    async def save(self, rule: NotificationRule) -> None:
        t_type, t_resource = _serialize_trigger(rule.trigger)
        await self.session.execute(
            update(notification_rules)
            .where(notification_rules.c.id == rule.id)
            .values(
                trigger_type=t_type,
                trigger_resource=t_resource,
                connection_string=(
                    f"{rule.connection.integration}://"
                    f"{rule.connection.resource}"
                ),
                message_template=rule.message_template,
                rate_limit_s=rule.rate_limit.seconds,
            )
        )

    @override
    async def get_by_id(
        self, rule_id: NotificationRuleId
    ) -> NotificationRule | None:
        result = await self.session.execute(
            select(notification_rules)
            .where(notification_rules.c.id == rule_id)
        )
        row = result.first()
        if not row:
            return None
        return _row_to_rule(row)

    @override
    async def get_by_ids(
        self, ids: list[NotificationRuleId]
    ) -> list[NotificationRule]:
        if not ids:
            return []
        result = await self.session.execute(
            select(notification_rules)
            .where(notification_rules.c.id.in_(ids))
        )
        return list(map(_row_to_rule, result.all()))

    @override
    async def all(
        self, pagination: Pagination | None
    ) -> list[NotificationRule]:
        query = select(notification_rules)
        if pagination:
            query = query.limit(pagination.limit).offset(pagination.offset)
        result = await self.session.execute(query)
        return list(map(_row_to_rule, result.all()))

    @override
    async def all_of_trigger_type(
        self, trigger_type: str
    ) -> list[NotificationRule]:
        result = await self.session.execute(
            select(notification_rules)
            .where(notification_rules.c.trigger_type == trigger_type)
        )
        return list(map(_row_to_rule, result.all()))

    @override
    async def delete(self, rule_id: NotificationRuleId) -> None:
        await self.session.execute(
            delete(notification_rules).where(
                notification_rules.c.id == rule_id
            )
        )


def _serialize_trigger(trigger: Trigger) -> tuple[str, str]:
    match trigger:
        case AnyExperimentTrigger():
            return "experiment_lifecycle", "*"
        case ExperimentTrigger(experiment_id=eid):
            return "experiment_lifecycle", str(eid)
        case GuardrailTrigger(guardrail_id=gid):
            return "guardrail", str(gid)
        case _:
            assert_never(trigger)


def _row_to_rule(row: Row[Any]) -> NotificationRule:
    trigger: Trigger
    match (row.trigger_type, row.trigger_resource):
        case ("experiment_lifecycle", "*"):
            trigger = AnyExperimentTrigger()
        case ("experiment_lifecycle", res):
            trigger = ExperimentTrigger(ExperimentId(res))
        case ("guardrail", res):
            trigger = GuardrailTrigger(GuardRuleId(res))
        case _:
            raise ValueError(
                f"Unknown trigger stored "
                f"{row.trigger_type}:{row.trigger_resource}"
            )
    return NotificationRule(
        id=NotificationRuleId(row.id),
        trigger=trigger,
        connection=ConnectionString(row.connection_string),
        message_template=row.message_template,
        rate_limit=Ratelimit(row.rate_limit_s),
    )


class SqlPreparedNotificationQueue(PreparedNotificationQueue):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def push_all(
        self, notifications: list[PreparedNotification]
    ) -> None:
        if not notifications:
            return
        stmt = pg_insert(prepared_notifications).values(
            [
                {
                    "fingerprint": notification.fingerprint,
                    "rule_id": notification.rule_id,
                    "meta": notification.meta,
                    "issued_at": notification.issued_at,
                }
                for notification in notifications
            ]
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["fingerprint"],
                set_={"issued_at": stmt.excluded.issued_at},
            )
        )

    @override
    async def all(self) -> list[PreparedNotification]:
        result = await self.session.execute(select(prepared_notifications))
        return list(map(_row_to_notification, result.all()))

    @override
    async def pop_all(self, fingerprints: list[Fingerprint]) -> None:
        if not fingerprints:
            return
        await self.session.execute(
            delete(prepared_notifications)
            .where(prepared_notifications.c.fingerprint.in_(fingerprints))
        )


def _row_to_notification(row: Row[Any]) -> PreparedNotification:
    return PreparedNotification(
        fingerprint=Fingerprint(row.fingerprint),
        rule_id=NotificationRuleId(row.rule_id),
        meta=cast(dict[str, str], row.meta),
        issued_at=row.issued_at,
    )
