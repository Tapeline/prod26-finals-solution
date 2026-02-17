from typing import Any, override

from adaptix import Retort, dumper, loader
from sqlalchemy import Row, insert, select, update

from alphabet.experiments.application.interfaces import ExperimentsRepository
from alphabet.experiments.domain.experiment import (
    ConflictDomain,
    Experiment,
    ExperimentId,
    ExperimentName,
    ExperimentResult,
    ExperimentState,
    MetricCollection,
    Percentage,
    Priority,
    Variant,
)
from alphabet.experiments.domain.flags import FlagKey
from alphabet.experiments.domain.target_rule import TargetRuleString
from alphabet.experiments.infrastructure.tables import (
    experiments_history,
    experiments_latest,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.domain.user import UserId
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


class SqlExperimentsRepository(ExperimentsRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def get_latest_by_id(
        self,
        exp_id: ExperimentId,
        *,
        lock: bool = False,
    ) -> Experiment | None:
        query = select(experiments_latest).where(
            experiments_latest.c.id == exp_id,
        )
        if lock:
            query = query.with_for_update()
        row = (await self.session.execute(query)).first()
        if not row:
            return None
        return _row_to_experiment(row)

    @override
    async def get_by_id_and_version(
        self,
        exp_id: ExperimentId,
        version: int,
    ) -> Experiment | None:
        result = await self.session.execute(
            select(experiments_history).where(
                experiments_history.c.id == exp_id,
                experiments_history.c.version == version,
            ),
        )
        row = result.first()
        if not row:
            return None
        return _row_to_experiment(row)

    @override
    async def get_old_versions(self, exp_id: ExperimentId) -> list[Experiment]:
        result = await self.session.execute(
            select(experiments_history).where(
                experiments_history.c.id == exp_id,
            ),
        )
        return list(map(_row_to_experiment, result.all()))

    @override
    async def create(self, experiment: Experiment) -> None:
        await self.session.execute(
            insert(experiments_latest).values(
                id=experiment.id,
                name=experiment.name.value,
                flag_key=experiment.flag_key.value,
                state=experiment.state,
                version=experiment.version,
                audience=experiment.audience.value,
                variants=_retort.dump(experiment.variants, list[Variant]),
                targeting=experiment.targeting.value
                if experiment.targeting
                else None,
                author_id=experiment.author_id,
                created_at=experiment.created_at,
                updated_at=experiment.updated_at,
                result_comment=experiment.result.comment
                if experiment.result
                else None,
                result_outcome=experiment.result.outcome
                if experiment.result
                else None,
                metrics=_retort.dump(experiment.metrics),
                priority=experiment.priority.value
                if experiment.priority
                else None,
                conflict_domain=experiment.conflict_domain,
                conflict_policy=experiment.conflict_policy,
            ),
        )

    @override
    async def save(self, experiment: Experiment) -> None:
        await self.session.execute(
            insert(experiments_history).from_select(
                experiments_latest.c.keys(),
                select(experiments_latest).where(
                    experiments_latest.c.id == experiment.id,
                ),
            ),
        )
        await self.session.execute(
            update(experiments_latest)
            .where(experiments_latest.c.id == experiment.id)
            .values(
                name=experiment.name.value,
                flag_key=experiment.flag_key.value,
                state=experiment.state,
                version=experiment.version,
                audience=experiment.audience.value,
                variants=_retort.dump(experiment.variants, list[Variant]),
                targeting=experiment.targeting.value
                if experiment.targeting
                else None,
                author_id=experiment.author_id,
                created_at=experiment.created_at,
                updated_at=experiment.updated_at,
                result_comment=experiment.result.comment
                if experiment.result
                else None,
                result_outcome=experiment.result.outcome
                if experiment.result
                else None,
                metrics=_retort.dump(experiment.metrics),
                priority=experiment.priority.value
                if experiment.priority
                else None,
                conflict_domain=experiment.conflict_domain,
                conflict_policy=experiment.conflict_policy,
            ),
        )

    @override
    async def get_active_by_flag(self, flag_key: FlagKey) -> Experiment | None:
        result = await self.session.execute(
            select(experiments_latest).where(
                experiments_latest.c.state == ExperimentState.STARTED,
                experiments_latest.c.flag_key == flag_key.value,
            ),
        )
        row = result.first()
        if not row:
            return None
        return _row_to_experiment(row)

    @override
    async def all(self, pagination: Pagination) -> list[Experiment]:
        result = await self.session.execute(
            select(experiments_latest)
            .limit(pagination.limit)
            .offset(pagination.offset),
        )
        return list(map(_row_to_experiment, result.all()))

    @override
    async def all_running(self) -> list[Experiment]:
        result = await self.session.execute(
            select(experiments_latest).where(
                experiments_latest.c.state == ExperimentState.STARTED,
            ),
        )
        return list(map(_row_to_experiment, result.all()))


_retort = Retort(
    recipe=[
        loader(Percentage, lambda x: Percentage(x)),  # noqa: PLW0108
        dumper(Percentage, lambda p: p.value),
    ],
)


def _row_to_experiment(row: Row[Any]) -> Experiment:
    variants = _retort.load(row.variants, list[Variant])
    metrics = _retort.load(row.metrics, MetricCollection)
    if row.result_comment and row.result_outcome:
        result = ExperimentResult(
            row.result_comment,
            row.result_outcome,
        )
    else:
        result = None
    return Experiment(
        _id=ExperimentId(row.id),
        _name=ExperimentName(row.name),
        _flag_key=FlagKey(row.flag_key),
        _state=row.state,
        _version=row.version,
        _audience=Percentage(row.audience),
        _variants=variants,
        _targeting=TargetRuleString(row.targeting) if row.targeting else None,
        _author_id=UserId(row.author_id),
        _created_at=row.created_at,
        _updated_at=row.updated_at,
        _metrics=metrics,
        _priority=Priority(row.priority) if row.priority else None,
        _conflict_domain=ConflictDomain(row.conflict_domain)
        if row.conflict_domain
        else None,
        _conflict_policy=row.conflict_policy,
        _result=result,
    )
