from collections.abc import Sequence
from typing import Any, final

from adaptix.conversion import get_converter
from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, Request, get
from msgspec import Struct

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.insights.application import InsightsDTO, ViewInsights
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_NOT_AUTHENTICATED,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs


@final
class InsightsResponse(Struct):
    real_distribution: dict[str, int]
    event_statuses: dict[str, int]
    event_types: dict[str, int]
    rejection_reasons: dict[str, int]
    attribution_fullness_percentage: float
    delivery_latency_p95_ms: float
    delivery_latency_p75_ms: float
    delivery_latency_p50_ms: float


_converter = get_converter(InsightsDTO, InsightsResponse)


class InsightsController(Controller):
    path = "/api/v1/insights"
    tags: Sequence[str] | None = ("Insights",)
    security = security_defs

    @get(
        "/{exp_id:str}",
        responses={
            200: success_spec("Retrieved.", InsightsResponse),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_insights(
        self,
        exp_id: str,
        interactor: FromDishka[ViewInsights],
        request: Request[Any, Any, Any],
    ) -> InsightsResponse:
        insights = await interactor(
            ExperimentId(exp_id),
            dict(request.query_params.items()),
        )
        return _converter(insights)
