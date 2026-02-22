from typing import final

from alphabet.decisions.application import AssignmentStore
from alphabet.experiments.application.interfaces import ExperimentsRepository
from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.application.interfaces import (
    MetricEvaluator,
    DSLCompiler,
)
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import UserReader, require_any_user
from alphabet.shared.commons import interactor, dto


@dto
@final
class InsightsDTO:
    real_distribution: dict[str, int]
    event_statuses: dict[str, int]
    event_types: dict[str, int]
    rejection_reasons: dict[str, int]
    attribution_fullness_percentage: float
    delivery_latency_p95_ms: float
    delivery_latency_p75_ms: float
    delivery_latency_p50_ms: float


@final
@interactor
class ViewInsights:
    idp: UserIdProvider
    user_reader: UserReader
    assignment_store: AssignmentStore
    tx: TransactionManager
    evaluator: MetricEvaluator
    experiments: ExperimentsRepository
    compiler: DSLCompiler
    time: TimeProvider

    async def __call__(
        self, target: ExperimentId, filters: dict[str, str]
    ) -> InsightsDTO:
        print(filters)
        async with self.tx:
            await require_any_user(self)
            distribution = \
                await self.assignment_store.get_variant_distribution(target)
            insights = await self.evaluator.query_insights(target, filters)
            return InsightsDTO(
                real_distribution=distribution,
                delivery_latency_p95_ms=insights.delivery_latency_p95_ms,
                delivery_latency_p75_ms=insights.delivery_latency_p75_ms,
                delivery_latency_p50_ms=insights.delivery_latency_p50_ms,
                event_statuses=insights.event_statuses,
                event_types=insights.event_types,
                rejection_reasons=insights.rejection_reasons,
                attribution_fullness_percentage=
                insights.attribution_fullness_percentage,
            )
