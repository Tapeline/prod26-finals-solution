from collections.abc import Sequence

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post
from msgspec import Struct

from alphabet.metrics.application.interactors import (
    CreateMetric,
    CreateMetricDTO,
    ListMetrics,
    ReadMetric,
    UpdateMetric,
)
from alphabet.metrics.domain.metrics import (
    Metric,
    MetricKey,
    SQLFragment,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_FORBIDDEN,
    RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    RESPONSE_NOT_FOUND,
    error_spec,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs


class MetricSchema(Struct):
    key: str
    expr: str
    compiled: tuple[SQLFragment, SQLFragment | None]

    @classmethod
    def from_metric(cls, metric: Metric) -> "MetricSchema":
        return MetricSchema(
            key=metric.key.value,
            expr=metric.expression,
            compiled=metric.compiled_expression,
        )


class CreateMetricRequest(Struct):
    key: str
    expr: str


class UpdateMetricRequest(Struct):
    expr: str


class MetricsController(Controller):
    path = "/api/v1/metrics"
    tags: Sequence[str] | None = ("Metrics",)
    security = security_defs

    @post(
        path="/create",
        responses={
            201: success_spec("Created.", MetricSchema),
            409: error_spec("Already exists."),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_metric(
        self,
        data: CreateMetricRequest,
        interactor: FromDishka[CreateMetric],
    ) -> MetricSchema:
        metric = await interactor(
            CreateMetricDTO(
                key=MetricKey(data.key),
                expression=data.expr,
            ),
        )
        return MetricSchema.from_metric(metric)

    @get(
        path="",
        responses={
            200: success_spec("Retrieved.", list[MetricSchema]),
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
    )
    @inject
    async def list_metrics(
        self,
        interactor: FromDishka[ListMetrics],
        limit: int = 50,
        offset: int = 0,
    ) -> list[MetricSchema]:
        metrics = await interactor(Pagination(limit, offset))
        return list(map(MetricSchema.from_metric, metrics))

    @patch(
        path="/{metric_key:str}",
        responses={
            200: success_spec("Updated.", MetricSchema),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def update_metric(
        self,
        metric_key: str,
        interactor: FromDishka[UpdateMetric],
        data: UpdateMetricRequest,
    ) -> MetricSchema:
        metric = await interactor(MetricKey(metric_key), data.expr)
        return MetricSchema.from_metric(metric)

    @get(
        path="/{metric_key:str}",
        responses={
            200: success_spec("Retrieved.", MetricSchema),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def read_metric(
        self,
        metric_key: str,
        interactor: FromDishka[ReadMetric],
    ) -> MetricSchema:
        metric = await interactor(MetricKey(metric_key))
        return MetricSchema.from_metric(metric)
