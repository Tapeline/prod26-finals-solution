import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import assert_never, cast, final

from structlog import getLogger

from alphabet.experiments.application.interfaces import (
    ExperimentChangeNotifier,
    ExperimentsRepository,
)
from alphabet.experiments.domain.experiment import (
    Experiment,
    ExperimentId,
    ExperimentState,
)
from alphabet.guardrails.application.exceptions import GuardRuleNotFound
from alphabet.guardrails.application.interfaces import (
    AuditLog,
    GuardRuleRepository,
)
from alphabet.guardrails.domain import (
    AuditRecord,
    AuditRecordId,
    GuardAction,
    GuardRule,
    GuardRuleId,
)
from alphabet.metrics.application.interfaces import (
    MetricEvaluator,
    MetricRepository,
)
from alphabet.metrics.domain.metrics import Metric, MetricKey
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

logger = getLogger(__name__)


@final
@dto
class CreateRuleDTO:
    metric_key: MetricKey
    threshold: float
    watch_window: timedelta
    action: GuardAction


@final
@interactor
class CreateRule:
    user_reader: UserReader
    idp: UserIdProvider
    rules: GuardRuleRepository
    tx: TransactionManager

    async def __call__(
        self,
        experiment_id: ExperimentId,
        dto: CreateRuleDTO,
    ) -> GuardRule:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            rule = GuardRule(
                id=generate_id(GuardRuleId),
                experiment_id=experiment_id,
                metric_key=dto.metric_key,
                threshold=dto.threshold,
                watch_window=dto.watch_window,
                action=dto.action,
                is_archived=False,
            )
            await self.rules.create(rule)
            return rule


@final
@dto
class UpdateRuleDTO:
    threshold: Maybe[float]
    watch_window: Maybe[timedelta]
    action: Maybe[GuardAction]


@final
@interactor
class UpdateRule:
    user_reader: UserReader
    idp: UserIdProvider
    rules: GuardRuleRepository
    tx: TransactionManager

    async def __call__(
        self,
        target: GuardRuleId,
        dto: UpdateRuleDTO,
    ) -> GuardRule:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            rule = await self.rules.get_by_id(target)
            if not rule:
                raise GuardRuleNotFound
            if dto.action is not MISSING:
                rule.action = cast(GuardAction, dto.action)
            if dto.threshold is not MISSING:
                rule.threshold = cast(float, dto.threshold)
            if dto.watch_window is not MISSING:
                rule.watch_window = cast(timedelta, dto.watch_window)
            await self.rules.save(rule)
            return rule


@final
@interactor
class ArchiveRule:
    user_reader: UserReader
    idp: UserIdProvider
    rules: GuardRuleRepository
    tx: TransactionManager

    async def __call__(self, target: GuardRuleId) -> GuardRule:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            rule = await self.rules.get_by_id(target)
            if not rule:
                raise GuardRuleNotFound
            rule.is_archived = True
            await self.rules.save(rule)
            return rule


@final
@interactor
class ReadRule:
    user_reader: UserReader
    idp: UserIdProvider
    rules: GuardRuleRepository
    tx: TransactionManager

    async def __call__(
        self,
        target: GuardRuleId,
    ) -> GuardRule:
        async with self.tx:
            await require_any_user(self)
            rule = await self.rules.get_by_id(target)
            if not rule:
                raise GuardRuleNotFound
            return rule


@final
@interactor
class ReadRulesForExperiment:
    user_reader: UserReader
    idp: UserIdProvider
    rules: GuardRuleRepository
    tx: TransactionManager

    async def __call__(
        self,
        experiment_id: ExperimentId,
    ) -> list[GuardRule]:
        async with self.tx:
            await require_any_user(self)
            return await self.rules.for_experiment(experiment_id)


@final
@interactor
class ReadAuditForExperiment:
    user_reader: UserReader
    idp: UserIdProvider
    audit_log: AuditLog
    tx: TransactionManager

    async def __call__(
        self,
        experiment_id: ExperimentId,
        pagination: Pagination,
    ) -> list[AuditRecord]:
        async with self.tx:
            await require_any_user(self)
            return await self.audit_log.query_for_experiment(
                experiment_id,
                pagination,
            )


@final
@interactor
class ReadAuditForGuardRule:
    user_reader: UserReader
    idp: UserIdProvider
    audit_log: AuditLog
    tx: TransactionManager

    async def __call__(
        self,
        rule_id: GuardRuleId,
        pagination: Pagination,
    ) -> list[AuditRecord]:
        async with self.tx:
            await require_any_user(self)
            return await self.audit_log.query_for_rule(rule_id, pagination)


@final
@interactor
class RegularCheck:
    rules: GuardRuleRepository
    audit_log: AuditLog
    tx: TransactionManager
    experiments: ExperimentsRepository
    evaluator: MetricEvaluator
    time: TimeProvider
    metrics: MetricRepository
    notifier: ExperimentChangeNotifier

    async def __call__(self) -> None:
        # avoiding n+1, preloading everything in 3 queries
        # WARNING: not concurrency-safe. Modifying can mess up
        logger.info("Regular guardrail check begin")
        start_time = self.time.now_unix_timestamp()
        running = await self.experiments.all_running()
        all_rules = defaultdict(list)
        all_metric_keys = []
        for rule in await self.rules.for_experiments(
            [experiment.id for experiment in running],
        ):
            all_rules[rule.experiment_id].append(rule)
            all_metric_keys.append(rule.metric_key)
        all_metrics = {
            metric.key: metric
            for metric in await self.metrics.get_by_keys(all_metric_keys)
        }
        await asyncio.gather(
            *(
                self._revise_experiment(experiment, all_rules, all_metrics)
                for experiment in running
            ),
        )
        logger.info(
            "Regular guardrail check finished",
            elapsed_s=self.time.now_unix_timestamp() - start_time,
            rules_checked=sum(map(len, all_rules.values())),
            experiments_checked=len(running),
        )

    async def _revise_experiment(
        self,
        experiment: Experiment,
        all_rules: dict[ExperimentId, list[GuardRule]],
        all_metrics: dict[MetricKey, Metric],
    ) -> None:
        now = self.time.now()
        rules = all_rules[experiment.id]
        targeted = [
            (rule, metric)
            for rule in rules
            if (metric := all_metrics.get(rule.metric_key))
        ]
        # maybe optimise by batching together
        # metrics with the same rule window
        await asyncio.gather(
            *(
                self._revise_rule(experiment, rule, metric, now)
                for rule, metric in targeted
            ),
        )

    async def _revise_rule(
        self,
        exp: Experiment,
        rule: GuardRule,
        metric: Metric,
        now: datetime,
    ) -> None:
        result = (
            await self.evaluator.evaluate_only_overall_for_experiment(
                exp.id,
                [metric],
                now - rule.watch_window,
                now,
            )
        ).get(metric.key)
        if result is None:
            logger.warning(
                "Received None instead of metric value",
                experiment_id=exp.id,
                rule_id=rule.id,
                metric_key=metric.key.value,
            )
        elif result > rule.threshold:
            logger.info(
                "Threshold exceeded for guardrail",
                experiment_id=exp.id,
                rule_id=rule.id,
                metric_key=metric.key.value,
            )
            await self._take_action(exp.id, rule, metric, result, now)

    async def _take_action(
        self,
        experiment_id: ExperimentId,
        rule: GuardRule,
        metric: Metric,
        value: float,
        now: datetime,
    ) -> None:
        # idk if this is good
        async with self.tx:
            # get again to prevent data loss
            fresh_experiment = await self.experiments.get_latest_by_id(
                experiment_id,
                lock=True,
            )
            if not fresh_experiment:
                logger.error(
                    "Experiment not found when taking action",
                    experiment_id=experiment_id,
                )
                return
            match rule.action:
                case GuardAction.PAUSE:
                    fresh_experiment.state = ExperimentState.PAUSED
                    await self.notifier.notify_experiment_deactivated(
                        fresh_experiment,
                    )
                case GuardAction.FORCE_CONTROL:
                    fresh_experiment.state = ExperimentState.SECURITY_HALTED
                    await self.notifier.notify_experiment_halted(
                        fresh_experiment,
                    )
                case _:
                    assert_never(rule.action)
            record = AuditRecord(
                id=generate_id(AuditRecordId),
                rule_id=rule.id,
                fired_at=now,
                experiment_id=experiment_id,
                metric_key=metric.key,
                metric_value=value,
                taken_action=rule.action,
            )
            logger.info(
                "Taken guardrail action for experiment",
                experiment_id=experiment_id,
                rule_id=rule.id,
                metric_key=metric.key.value,
                action=rule.action,
            )
            await self.audit_log.write(record)
            await self.experiments.save(fresh_experiment)
