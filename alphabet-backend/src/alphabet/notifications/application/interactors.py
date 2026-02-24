import asyncio
from collections import defaultdict
from typing import assert_never, cast, final

from structlog import getLogger

from alphabet.experiments.domain.experiment import Experiment
from alphabet.guardrails.domain import AuditRecord
from alphabet.notifications.application.exceptions import (
    FailedToSend,
    RuleNotFound,
)
from alphabet.notifications.application.interfaces import (
    GroupedNotificationBuilder,
    NotificationChannelFactory,
    NotificationCooldownStore,
    NotificationRuleRepository,
    PreparedNotificationQueue,
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
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import (
    UserReader,
    require_any_user,
    require_user_with_role,
)
from alphabet.shared.commons import MISSING, Maybe, dto, interactor
from alphabet.shared.domain.user import Role
from alphabet.shared.uuid import generate_id


@dto
@final
class CreateRuleDTO:
    trigger: Trigger
    connection: ConnectionString
    template: str
    rate_limit: Ratelimit


@final
@interactor
class CreateNotificationRule:
    idp: UserIdProvider
    user_reader: UserReader
    rules: NotificationRuleRepository
    tx: TransactionManager

    async def __call__(self, dto: CreateRuleDTO) -> NotificationRule:
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER, Role.APPROVER},
            )
            rule = NotificationRule(
                id=generate_id(NotificationRuleId),
                trigger=dto.trigger,
                connection=dto.connection,
                message_template=dto.template,
                rate_limit=dto.rate_limit,
            )
            await self.rules.create(rule)
            return rule


@dto
@final
class UpdateRuleDTO:
    trigger: Maybe[Trigger]
    connection: Maybe[ConnectionString]
    template: Maybe[str]
    rate_limit: Maybe[Ratelimit]


@final
@interactor
class UpdateNotificationRule:
    idp: UserIdProvider
    user_reader: UserReader
    rules: NotificationRuleRepository
    tx: TransactionManager

    async def __call__(
        self,
        target: NotificationRuleId,
        dto: UpdateRuleDTO,
    ) -> NotificationRule:
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER, Role.APPROVER},
            )
            rule = await self.rules.get_by_id(target)
            if not rule:
                raise RuleNotFound
            if dto.trigger is not MISSING:
                rule.trigger = cast(Trigger, dto.trigger)
            if dto.connection is not MISSING:
                rule.connection = cast(ConnectionString, dto.connection)
            if dto.template is not MISSING:
                rule.message_template = cast(str, dto.template)
            if dto.rate_limit is not MISSING:
                rule.rate_limit = cast(Ratelimit, dto.rate_limit)
            await self.rules.save(rule)
            return rule


@final
@interactor
class DeleteNotificationRule:
    idp: UserIdProvider
    user_reader: UserReader
    rules: NotificationRuleRepository
    tx: TransactionManager

    async def __call__(self, target: NotificationRuleId) -> None:
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER, Role.APPROVER},
            )
            rule = await self.rules.get_by_id(target)
            if not rule:
                raise RuleNotFound
            await self.rules.delete(rule.id)


@final
@interactor
class ReadNotificationRule:
    idp: UserIdProvider
    user_reader: UserReader
    rules: NotificationRuleRepository
    tx: TransactionManager

    async def __call__(self, target: NotificationRuleId) -> NotificationRule:
        async with self.tx:
            await require_any_user(self)
            rule = await self.rules.get_by_id(target)
            if not rule:
                raise RuleNotFound
            return rule


@final
@interactor
class ReadAllNotificationRule:
    idp: UserIdProvider
    user_reader: UserReader
    rules: NotificationRuleRepository
    tx: TransactionManager

    async def __call__(self, pagination: Pagination) -> list[NotificationRule]:
        async with self.tx:
            await require_any_user(self)
            return await self.rules.all(pagination)


@dto
@final
class ExperimentEvent:
    experiment: Experiment


@dto
@final
class GuardrailEvent:
    record: AuditRecord


type Event = ExperimentEvent | GuardrailEvent

logger = getLogger(__name__)


@final
@interactor
class PublishNotification:
    rules: NotificationRuleRepository
    tx: TransactionManager
    time: TimeProvider
    notification_queue: PreparedNotificationQueue

    async def __call__(self, event: Event) -> None:
        async with self.tx:
            match event:
                case ExperimentEvent(experiment):
                    await self._maybe_publish_experiment_event(experiment)
                case GuardrailEvent(record):
                    await self._maybe_publish_guardrail_event(record)
                case _:
                    assert_never(event)

    async def _maybe_publish_experiment_event(
        self,
        experiment: Experiment,
    ) -> None:
        rules = await self.rules.all_of_trigger_type("experiment_lifecycle")
        selected = []
        for rule in rules:
            match rule.trigger:
                case ExperimentTrigger(experiment_id):
                    if experiment.id == experiment_id:
                        selected.append(rule)
                case AnyExperimentTrigger():
                    selected.append(rule)
        now = self.time.now()
        meta = {
            "state": experiment.state.value,
            "id": experiment.id,
            "iat": now.isoformat(),
        }
        await self.notification_queue.push_all(
            [
                PreparedNotification(
                    fingerprint=Fingerprint(
                        f"{rule.id}:{experiment.id}:{experiment.state}",
                    ),
                    rule_id=rule.id,
                    meta=meta,
                    issued_at=now,
                )
                for rule in selected
            ],
        )

    async def _maybe_publish_guardrail_event(
        self,
        record: AuditRecord,
    ) -> None:
        rules = await self.rules.all_of_trigger_type("guardrail")
        selected = []
        for rule in rules:
            match rule.trigger:
                case GuardrailTrigger(guardrail_id):
                    if record.rule_id == guardrail_id:
                        selected.append(rule)
        now = self.time.now()
        meta = {
            "audit_id": record.id,
            "rule_id": record.rule_id,
            "taken_action": record.taken_action.value,
            "fired_at": record.fired_at.isoformat(),
            "metric_key": record.metric_key.value,
            "metric_value": str(record.metric_value),
            "experiment_id": record.experiment_id,
            "iat": now.isoformat(),
        }
        await self.notification_queue.push_all(
            [
                PreparedNotification(
                    fingerprint=Fingerprint(f"{rule.id}:{record.rule_id}"),
                    rule_id=rule.id,
                    meta=meta,
                    issued_at=now,
                )
                for rule in selected
            ],
        )


@final
@interactor
class SelectAndSend:
    queue: PreparedNotificationQueue
    tx: TransactionManager
    limiter: NotificationCooldownStore
    rules: NotificationRuleRepository
    channel_factory: NotificationChannelFactory
    builder: GroupedNotificationBuilder

    async def __call__(self) -> None:
        logger.info("Begin select and send")
        async with self.tx:
            notifications = self._group_by_rule_id(await self.queue.all())
            logger.info("Selected pending", total=len(notifications))
            exclude = await self.limiter.filter_in_cooldown(
                notifications.keys(),
            )
            for rule_id in exclude:
                notifications.pop(rule_id)
            logger.debug(
                "Excluded those in cooldown",
                excluded=len(exclude),
                remaining=len(notifications),
            )
            rule_ids = list(notifications.keys())
            rules = await self.rules.get_by_ids(rule_ids)
            successfully_sent = await asyncio.gather(
                *(
                    self._send_group(rule, notifications[rule.id])
                    for rule in rules
                ),
            )
            ack_fingerprints = []
            for sent_group in successfully_sent:
                ack_fingerprints.extend(sent_group)
            logger.info(
                "Sent notifications",
                ok=len(ack_fingerprints),
                total=sum(map(len, notifications.values())),
                cooldown_excluded=len(exclude),
            )
            await self.queue.pop_all(ack_fingerprints)
            await self.limiter.place_cooldowns(
                {rule.id: rule.rate_limit.seconds for rule in rules},
            )

    def _group_by_rule_id(
        self,
        notifications: list[PreparedNotification],
    ) -> dict[NotificationRuleId, list[PreparedNotification]]:
        grouped = defaultdict(list)
        for notification in notifications:
            grouped[notification.rule_id].append(notification)
        return grouped

    async def _send_group(
        self,
        rule: NotificationRule,
        notifications: list[PreparedNotification],
    ) -> list[Fingerprint]:
        """Send and return list of successfully sent fingerprints."""
        logger.info(
            "Sending batch",
            sink=rule.connection,
            total=len(notifications),
        )
        channel = self.channel_factory.create(rule.connection)
        message = self.builder.render_merge(
            rule.message_template,
            notifications,
        )
        try:
            await channel.send(message)
        except FailedToSend as exc:
            logger.exception(
                "Failed to send notification group for rule",
                rule=rule,
                exc=exc,
            )
            return []
        else:
            return [notif.fingerprint for notif in notifications]
