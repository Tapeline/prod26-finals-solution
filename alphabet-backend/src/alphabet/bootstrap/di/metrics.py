from dishka import Provider, Scope, provide, provide_all

from alphabet.metrics.application.interactors import (
    CreateMetric,
    CreateReport,
    DeleteReport,
    GetReportResult,
    ListMetrics,
    ReadMetric,
    UpdateMetric,
)
from alphabet.metrics.application.interfaces import (
    MetricEvaluator,
    MetricRepository,
    ReportRepository,
)
from alphabet.metrics.infrastructure.evaluator import ClickHouseMetricEvaluator
from alphabet.metrics.infrastructure.repos import (
    SqlMetricRepository,
    SqlReportRepository,
)


class MetricsDIProvider(Provider):
    interactors = provide_all(
        CreateMetric,
        ListMetrics,
        ReadMetric,
        UpdateMetric,
        CreateReport,
        DeleteReport,
        GetReportResult,
        scope=Scope.REQUEST,
    )

    metrics_repo = provide(
        SqlMetricRepository,
        provides=MetricRepository,
        scope=Scope.REQUEST,
    )
    reports_repo = provide(
        SqlReportRepository,
        provides=ReportRepository,
        scope=Scope.REQUEST,
    )
    evaluator = provide(
        ClickHouseMetricEvaluator,
        provides=MetricEvaluator,
        scope=Scope.REQUEST,
    )

