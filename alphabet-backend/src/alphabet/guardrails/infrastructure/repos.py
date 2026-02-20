from datetime import timedelta
from typing import Any, final, override

from sqlalchemy import Row, insert, select, update

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.guardrails.application.interfaces import (
    AuditLog,
    GuardRuleRepository,
)
from alphabet.guardrails.domain import (
    AuditRecord,
    AuditRecordId,
    GuardRule,
    GuardRuleId,
)
from alphabet.guardrails.infrastructure.tables import audit_log, guard_rules
from alphabet.metrics.domain.metrics import (
    MetricKey,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


@final
class SqlAuditLog(AuditLog):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def write(self, record: AuditRecord) -> None:
        await self.session.execute(
            insert(audit_log).values(
                id=record.id,
                rule_id=record.rule_id,
                fired_at=record.fired_at,
                experiment_id=record.experiment_id,
                metric_key=record.metric_key.value,
                metric_value=record.metric_value,
                taken_action=record.taken_action,
            ),
        )

    @override
    async def query_for_experiment(
        self, exp_id: ExperimentId, pagination: Pagination,
    ) -> list[AuditRecord]:
        result = await self.session.execute(
            select(audit_log)
            .where(audit_log.c.experiment_id == exp_id)
            .limit(pagination.limit)
            .offset(pagination.offset),
        )
        return list(map(_row_to_audit_record, result.all()))

    @override
    async def query_for_rule(
        self, rule_id: GuardRuleId, pagination: Pagination,
    ) -> list[AuditRecord]:
        result = await self.session.execute(
            select(audit_log)
            .where(audit_log.c.rule_id == rule_id)
            .limit(pagination.limit)
            .offset(pagination.offset),
        )
        return list(map(_row_to_audit_record, result.all()))


def _row_to_audit_record(row: Row[Any]) -> AuditRecord:
    return AuditRecord(
        id=AuditRecordId(row.id),
        rule_id=GuardRuleId(row.rule_id),
        fired_at=row.fired_at,
        experiment_id=ExperimentId(row.experiment_id),
        metric_key=MetricKey(row.metric_key),
        metric_value=row.metric_value,
        taken_action=row.taken_action,
    )


class SqlGuardRuleRepository(GuardRuleRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def create(self, rule: GuardRule) -> None:
        await self.session.execute(
            insert(guard_rules).values(
                id=rule.id,
                experiment_id=rule.experiment_id,
                metric_key=rule.metric_key.value,
                threshold=rule.threshold,
                watch_window_s=rule.watch_window.total_seconds(),
                action=rule.action.value,
                is_archived=rule.is_archived,
            ),
        )

    @override
    async def save(self, rule: GuardRule) -> None:
        await self.session.execute(
            update(guard_rules)
            .where(guard_rules.c.id == rule.id)
            .values(
                threshold=rule.threshold,
                watch_window_s=int(rule.watch_window.total_seconds()),
                action=rule.action.value,
                is_archived=rule.is_archived,
            ),
        )

    @override
    async def get_by_id(self, rule_id: GuardRuleId) -> GuardRule | None:
        result = await self.session.execute(
            select(guard_rules).where(guard_rules.c.id == rule_id),
        )
        row = result.first()
        if not row:
            return None
        return _row_to_guard_rule(row)

    @override
    async def for_experiment(
        self, experiment_id: ExperimentId,
    ) -> list[GuardRule]:
        result = await self.session.execute(
            select(guard_rules).where(
                guard_rules.c.experiment_id == experiment_id,
                guard_rules.c.is_archived == False,  # noqa: E712
            ),
        )
        return list(map(_row_to_guard_rule, result.all()))

    @override
    async def for_experiments(
        self, experiment_ids: list[ExperimentId],
    ) -> list[GuardRule]:
        result = await self.session.execute(
            select(guard_rules).where(
                guard_rules.c.experiment_id.in_(experiment_ids),
                guard_rules.c.is_archived == False,  # noqa: E712
            ),
        )
        return list(map(_row_to_guard_rule, result.all()))


def _row_to_guard_rule(row: Row[Any]) -> GuardRule:
    return GuardRule(
        id=GuardRuleId(row.id),
        experiment_id=ExperimentId(row.experiment_id),
        metric_key=MetricKey(row.metric_key),
        threshold=row.threshold,
        watch_window=timedelta(seconds=row.watch_window_s),
        action=row.action,
        is_archived=row.is_archived,
    )
