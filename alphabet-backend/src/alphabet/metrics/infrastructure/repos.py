from typing import Any, final, override

from adaptix import Retort
from sqlalchemy import Row, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.application.interfaces import (
    MetricRepository,
    ReportRepository,
)
from alphabet.metrics.domain.exceptions import MetricAlreadyExists
from alphabet.metrics.domain.metrics import (
    Metric,
    MetricKey,
    Report,
    ReportId,
    ReportWindow,
    SQLFragment,
)
from alphabet.metrics.infrastructure.tables import metrics, reports
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.infrastructure.transaction import SqlTransactionManager

_retort = Retort()


@final
class SqlMetricRepository(MetricRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def create(self, metric: Metric) -> None:
        try:
            await self.session.execute(
                insert(metrics).values(
                    key=metric.key.value,
                    expression=metric.expression,
                    compiled=_dump_compiled(metric.compiled_expression),
                ),
            )
        except IntegrityError as exc:
            raise MetricAlreadyExists from exc

    @override
    async def save(self, metric: Metric) -> None:
        await self.session.execute(
            update(metrics)
            .where(metrics.c.key == metric.key.value)
            .values(
                expression=metric.expression,
                compiled=_dump_compiled(metric.compiled_expression),
            ),
        )

    @override
    async def get_by_key(self, key: MetricKey) -> Metric | None:
        row = (
            await self.session.execute(
                select(metrics).where(metrics.c.key == key.value),
            )
        ).first()
        if not row:
            return None
        return _row_to_metric(row)

    @override
    async def all(self, pagination: Pagination) -> list[Metric]:
        result = await self.session.execute(
            select(metrics).limit(pagination.limit).offset(pagination.offset),
        )
        return list(map(_row_to_metric, result.all()))

    @override
    async def get_by_keys(self, keys: list[MetricKey]) -> list[Metric]:
        result = await self.session.execute(
            select(metrics)
            .where(metrics.c.key.in_({key.value for key in keys}))
        )
        return list(map(_row_to_metric, result.all()))


def _row_to_metric(row: Row[Any]) -> Metric:
    return Metric(
        key=MetricKey(row.key),
        expression=row.expression,
        compiled_expression=_load_compiled(row.compiled),
    )


class SqlReportRepository(ReportRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def create(self, report: Report) -> None:
        await self.session.execute(
            insert(reports).values(
                id=report.id,
                experiment_id=report.experiment_id,
                start_at=report.window.start_at,
                end_at=report.window.end_at,
            ),
        )

    @override
    async def save(self, report: Report) -> None:
        await self.session.execute(
            update(reports)
            .where(reports.c.id == report.id)
            .values(
                experiment_id=report.experiment_id,
                start_at=report.window.start_at,
                end_at=report.window.end_at,
            ),
        )

    @override
    async def delete(self, report_id: ReportId) -> None:
        await self.session.execute(
            delete(reports).where(reports.c.id == report_id),
        )

    @override
    async def get_by_id(self, report_id: ReportId) -> Report | None:
        row = (
            await self.session.execute(
                select(reports).where(reports.c.id == report_id),
            )
        ).first()
        if not row:
            return None
        return _row_to_report(row)

    @override
    async def all_for_experiment(self, exp_id: ExperimentId) -> list[Report]:
        result = await self.session.execute(
            select(reports).where(reports.c.experiment_id == exp_id),
        )
        return list(map(_row_to_report, result.all()))


def _dump_compiled(
    compiled: tuple[SQLFragment, SQLFragment | None],
) -> list[dict[str, Any]]:
    return [
        _retort.dump(compiled[0], SQLFragment),
        _retort.dump(compiled[1], SQLFragment) if compiled[1] else None,
    ]


def _load_compiled(
    value: list[dict[str, Any]],
) -> tuple[SQLFragment, SQLFragment | None]:
    return (
        _retort.load(value[0], SQLFragment),
        _retort.load(value[1], SQLFragment) if value[1] else None,
    )


def _row_to_report(row: Row[Any]) -> Report:
    window = ReportWindow(
        start_at=row.start_at,
        end_at=row.end_at,
    )
    return Report(
        id=ReportId(row.id),
        experiment_id=row.experiment_id,
        window=window,
    )
