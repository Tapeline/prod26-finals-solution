from dataclasses import dataclass
from datetime import datetime
from typing import final

from alphabet.experiments.application.interfaces import ExperimentsRepository
from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.application.exceptions import ExperimentForReportNotFound
from alphabet.metrics.application.interfaces import (
    DSLCompiler,
    MetricEvaluator,
    MetricRepository,
    ReportRepository,
)
from alphabet.metrics.domain.exceptions import (
    NoSuchMetric,
    NoSuchReport,
)
from alphabet.metrics.domain.metrics import (
    Metric,
    MetricKey,
    Report,
    ReportId,
    ReportWindow,
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
from alphabet.shared.commons import interactor
from alphabet.shared.domain.user import Role
from alphabet.shared.uuid import generate_uuid


@final
@dataclass
class CreateMetricDTO:
    key: MetricKey
    expression: str


@final
@interactor
class CreateMetric:
    idp: UserIdProvider
    user_reader: UserReader
    metrics: MetricRepository
    tx: TransactionManager
    compiler: DSLCompiler

    async def __call__(self, dto: CreateMetricDTO) -> Metric:
        metric = Metric(
            key=dto.key,
            expression=dto.expression,
            compiled_expression=self.compiler.compile_dsl(dto.expression),
        )
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            await self.metrics.create(metric)
        return metric


@final
@interactor
class ListMetrics:
    metrics: MetricRepository
    tx: TransactionManager

    async def __call__(self, pagination: Pagination) -> list[Metric]:
        async with self.tx:
            return await self.metrics.all(pagination)


@final
@interactor
class UpdateMetric:
    metrics: MetricRepository
    tx: TransactionManager
    idp: UserIdProvider
    user_reader: UserReader
    compiler: DSLCompiler

    async def __call__(self, target: MetricKey, new_expr: str) -> Metric:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            # TODO: with for update?
            metric = await self.metrics.get_by_key(target)
            if not metric:
                raise NoSuchMetric
            metric.compiled_expression = self.compiler.compile_dsl(new_expr)
            metric.expression = new_expr
            await self.metrics.save(metric)
            return metric


@final
@interactor
class ReadMetric:
    metrics: MetricRepository
    tx: TransactionManager

    async def __call__(self, target: MetricKey) -> Metric:
        async with self.tx:
            metric = await self.metrics.get_by_key(target)
            if not metric:
                raise NoSuchMetric
            return metric


@final
@dataclass
class CreateReportDTO:
    experiment_id: ExperimentId
    start_at: datetime
    end_at: datetime


@final
@interactor
class CreateReport:
    reports: ReportRepository
    tx: TransactionManager
    idp: UserIdProvider
    user_reader: UserReader

    async def __call__(self, dto: CreateReportDTO) -> Report:

        report = Report(
            id=ReportId(generate_uuid()),
            experiment_id=dto.experiment_id,
            window=ReportWindow(dto.start_at, dto.end_at),
        )
        async with self.tx:
            await require_user_with_role(
                self, {Role.ADMIN, Role.EXPERIMENTER, Role.APPROVER},
            )
            await self.reports.create(report)
        return report


@final
@interactor
class DeleteReport:
    reports: ReportRepository
    tx: TransactionManager
    idp: UserIdProvider
    user_reader: UserReader

    async def __call__(self, report_id: ReportId) -> None:
        async with self.tx:
            await require_user_with_role(
                self, {Role.ADMIN, Role.EXPERIMENTER, Role.APPROVER},
            )
            report = await self.reports.get_by_id(report_id)
            if not report:
                raise NoSuchReport
            await self.reports.delete(report_id)


@final
@interactor
class ListReportsByExperiment:
    reports: ReportRepository
    tx: TransactionManager
    idp: UserIdProvider
    user_reader: UserReader

    async def __call__(self, experiment_id: ExperimentId) -> list[Report]:
        async with self.tx:
            await require_any_user(self)
            return await self.reports.all_for_experiment(experiment_id)


@final
@dataclass
class MetricPointDTO:
    key: str
    overall: float | None
    per_variant: dict[str, float | None]


@final
@dataclass
class ReportResultDTO:
    report_id: str
    experiment_id: str
    start_at: datetime
    end_at: datetime
    metrics: list[MetricPointDTO]


@final
@interactor
class GetReportResult:
    idp: UserIdProvider
    user_reader: UserReader
    reports: ReportRepository
    metrics: MetricRepository
    experiments: ExperimentsRepository
    evaluator: MetricEvaluator
    time: TimeProvider
    tx: TransactionManager

    async def __call__(self, report_id: ReportId) -> ReportResultDTO:
        # TODO: refactor later
        async with self.tx:
            await require_any_user(self)
            report = await self.reports.get_by_id(report_id)
            if not report:
                raise NoSuchReport

            experiment = await self.experiments.get_latest_by_id(
                report.experiment_id,
            )
            if not experiment:
                raise ExperimentForReportNotFound

            requested_keys = [
                MetricKey(experiment.metrics.primary),
                *[MetricKey(k) for k in experiment.metrics.secondary],
                *[MetricKey(k) for k in experiment.metrics.guarding],
            ]

            metric_models: list[Metric] = []
            for key in requested_keys:
                metric = await self.metrics.get_by_key(key)
                if metric:
                    metric_models.append(metric)

        eval_results = await self.evaluator.evaluate_for_experiment(
            experiment.id,
            # NOTE: `variant_id` in events is derived from decision_id and
            # currently contains variant *name* (see subject_events IncomingEventDTO).
            # So for correct per-variant aggregation we map by variant.name.
            {variant.name: variant.name for variant in experiment.variants},
            metric_models,
            report.window.start_at,
            report.window.end_at,
        )

        points: list[MetricPointDTO] = []
        for key in requested_keys:
            metric = next((m for m in metric_models if m.key == key), None)
            res = eval_results.get(key) if metric else None
            if res is None:
                points.append(
                    MetricPointDTO(
                        key=key.value,
                        overall=None,
                        per_variant={},
                    ),
                )
                continue
            points.append(
                MetricPointDTO(
                    key=key.value,
                    overall=res.overall,
                    per_variant=res.per_variant,
                ),
            )

        return ReportResultDTO(
            report_id=report.id,
            experiment_id=report.experiment_id,
            start_at=report.window.start_at,
            end_at=report.window.end_at,
            metrics=points,
        )
