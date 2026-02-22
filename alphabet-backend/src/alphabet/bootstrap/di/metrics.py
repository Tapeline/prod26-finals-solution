from dishka import Provider, Scope, provide, provide_all

from alphabet.metrics.application.interactors import (
    CreateMetric,
    CreateReport,
    DeleteReport,
    GetReportResult,
    ListMetrics,
    ListReportsByExperiment,
    ReadMetric,
    UpdateMetric,
)
from alphabet.metrics.application.interfaces import (
    DSLCompiler,
    MetricEvaluator,
    MetricRepository,
    ReportRepository,
)
from alphabet.metrics.infrastructure.dsl import ClickHouseDSLCompiler
from alphabet.metrics.infrastructure.evaluator import ClickHouseMetricEvaluator
from alphabet.metrics.infrastructure.repos import (
    SqlMetricRepository,
    SqlReportRepository,
)


class MetricsInteractorsDIProvider(Provider):
    interactors = provide_all(
        CreateMetric,
        ListMetrics,
        ReadMetric,
        UpdateMetric,
        CreateReport,
        DeleteReport,
        GetReportResult,
        ListReportsByExperiment,
        scope=Scope.REQUEST,
    )


class MetricsStorageDIProvider(Provider):
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
    ch_compiler = provide(
        ClickHouseDSLCompiler,
        provides=DSLCompiler,
        scope=Scope.APP,
    )


def get_metrics_providers() -> list[Provider]:
    return [
        MetricsInteractorsDIProvider(),
        MetricsStorageDIProvider(),
    ]
