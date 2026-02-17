from adaptix import Retort, loader
from typing import Any

from sqlalchemy import Row, insert, select, update

from alphabet.experiments.application.interfaces import ExperimentsRepository
from alphabet.experiments.domain.experiment import (
    Experiment,
    ExperimentId,
    ExperimentName,
    ExperimentResult, ExperimentState,
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

    async def get_latest_by_id(
        self,
        exp_id: ExperimentId,
        *,
        lock: bool = False
    ) -> Experiment | None:
        query = select(experiments_latest) \
            .where(experiments_latest.c.id == exp_id)
        if lock:
            query = query.with_for_update()
        result = (await self.session.execute(query)).first()
        return _row_to_experiment(result)

    async def get_by_id_and_version(
        self,
        exp_id: ExperimentId,
        version: int
    ) -> Experiment | None:
        result = await self.session.execute(
            select(experiments_history)
            .where(
                experiments_history.c.id == exp_id,
                experiments_history.c.version == version
            )
        )
        return _row_to_experiment(result.first())

    async def get_old_versions(self, exp_id: ExperimentId) -> list[Experiment]:
        result = await self.session.execute(
            select(experiments_history)
            .where(experiments_history.c.id == exp_id)
        )
        return list(map(_row_to_experiment, result.all()))

    async def create(self, experiment: Experiment) -> None:
        await self.session.execute(
            insert(experiments_latest).values(
                id=experiment.id,
                name=experiment.name.value,
                flag_key=experiment.flag_key.value,
                state=experiment.state,
                version=experiment.version,
                audience=experiment.audience.value,
                variants=_retort.dump(experiment.variants),
                targeting=experiment.targeting.value,
                author_id=experiment.author_id,
                created_at=experiment.created_at,
                updated_at=experiment.updated_at,
                result_comment=experiment.result.comment
                    if experiment.result else None,
                result_outcome=experiment.result.outcome
                    if experiment.result else None,
                metrics=_retort.dump(experiment.metrics),
                priority=experiment.priority.value,
                conflict_domain=experiment.conflict_domain,
                conflict_policy=experiment.conflict_policy,
            ),
        )

    async def save(self, experiment: Experiment) -> None:
        await self.session.execute(
            insert(experiments_history).from_select(
                experiments_latest.c.keys(),
                select(experiments_latest)
                .where(experiments_latest.c.id == experiment.id)
            )
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
                variants=_retort.dump(experiment.variants),
                targeting=experiment.targeting.value,
                author_id=experiment.author_id,
                created_at=experiment.created_at,
                updated_at=experiment.updated_at,
                result_comment=experiment.result.comment
                if experiment.result else None,
                result_outcome=experiment.result.outcome
                if experiment.result else None,
                metrics=_retort.dump(experiment.metrics),
                priority=experiment.priority.value,
                conflict_domain=experiment.conflict_domain,
                conflict_policy=experiment.conflict_policy,
            )
        )

    async def get_active_by_flag(self, flag_key: FlagKey) -> Experiment | None:
        result = await self.session.execute(
            select(experiments_latest)
            .where(
                experiments_latest.c.state == ExperimentState.STARTED,
                experiments_latest.c.flag_key == flag_key
            )
        )
        return _row_to_experiment(result.first())

    async def all(self, pagination: Pagination) -> list[Experiment]:
        result = await self.session.execute(
            select(experiments_latest)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        return list(map(_row_to_experiment, result.all()))


_retort = Retort(
    recipe=[
        loader(Percentage, lambda x: Percentage(x)),
    ]
)


def _row_to_experiment(row: Row[Any]) -> Experiment | None:
    if not row:
        return None
    variants = _retort.load(row.c.variants, list[Variant])
    metrics = _retort.load(row.c.metrics, MetricCollection)
    if row.c.result_comment and row.c.result_outcome:
        result = ExperimentResult(
            row.c.result_comment, row.c.result_outcome
        )
    else:
        result = None
    return Experiment(
        _id=ExperimentId(row.c.id),
        _name=ExperimentName(row.c.name),
        _flag_key=FlagKey(row.c.flag_key),
        _state=row.c.state,
        _version=row.c.version,
        _audience=Percentage(row.c.audience),
        _variants=variants,
        _targeting=TargetRuleString(row.c.targeting),
        _author_id=UserId(row.c.author_id),
        _created_at=row.c.created_at,
        _updated_at=row.c.updated_at,
        _metrics=metrics,
        _priority=Priority(row.c.priority),
        _conflict_domain=row.c.conflict_domain,
        _conflict_policy=row.c.conflict_policy,
        _result=result
    )
