from abc import abstractmethod
from datetime import datetime
from typing import Protocol, final

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.domain.metrics import (
    Metric,
    MetricKey,
    Report,
    ReportId,
    SQLFragment,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.commons import dto


class MetricRepository(Protocol):
    @abstractmethod
    async def create(self, metric: Metric) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, metric: Metric) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_key(self, key: MetricKey) -> Metric | None:
        raise NotImplementedError

    @abstractmethod
    async def all(self, pagination: Pagination) -> list[Metric]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_keys(self, keys: list[MetricKey]) -> list[Metric]:
        raise NotImplementedError


class ReportRepository(Protocol):
    @abstractmethod
    async def create(self, report: Report) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, report: Report) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, report_id: ReportId) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, report_id: ReportId) -> Report | None:
        raise NotImplementedError

    @abstractmethod
    async def all_for_experiment(self, exp_id: ExperimentId) -> list[Report]:
        raise NotImplementedError


@dto
@final
class MetricEvaluationResult:
    overall: float | None
    per_variant: dict[str, float | None]


@dto
@final
class EventInsights:
    event_statuses: dict[str, int]
    event_types: dict[str, int]
    rejection_reasons: dict[str, int]
    attribution_fullness_percentage: float
    delivery_latency_p95_ms: float
    delivery_latency_p75_ms: float
    delivery_latency_p50_ms: float


class MetricEvaluator(Protocol):
    @abstractmethod
    async def evaluate_for_experiment(
        self,
        experiment_id: str,
        variants: dict[str, str],
        metrics: list[Metric],
        start_at: datetime,
        end_at: datetime,
    ) -> dict[MetricKey, MetricEvaluationResult]:
        raise NotImplementedError

    @abstractmethod
    async def evaluate_only_overall_for_experiment(
        self,
        experiment_id: str,
        metrics: list[Metric],
        start_at: datetime,
        end_at: datetime,
    ) -> dict[MetricKey, float | None]:
        raise NotImplementedError

    @abstractmethod
    async def query_insights(
        self,
        experiment_id: str,
        filters: dict[str, str],
    ) -> EventInsights:
        raise NotImplementedError


class DSLCompiler(Protocol):
    @abstractmethod
    def compile_dsl(
        self,
        dsl_string: str,
    ) -> tuple[SQLFragment, SQLFragment | None]:
        raise NotImplementedError
