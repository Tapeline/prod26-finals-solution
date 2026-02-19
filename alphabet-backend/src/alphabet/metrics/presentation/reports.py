from collections.abc import Sequence
from datetime import datetime
from typing import Final

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, post, delete
from msgspec import Struct

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.application.interactors import (
    CreateMetric,
    CreateMetricDTO,
    CreateReport,
    CreateReportDTO,
    GetReportResult,
    ListMetrics,
    MetricPointDTO,
    ReportResultDTO,
    UpdateMetric,
    DeleteReport, ListReportsByExperiment,
)
from alphabet.metrics.domain.metrics import (
    MetricKey,
    ReportId,
    Metric,
    Report, SQLFragment,
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


class CreateMetricRequest(Struct):
    key: str
    expr: str


class CreateReportRequest(Struct):
    experiment_id: str
    start_at: datetime
    end_at: datetime


class MetricPointResponse(Struct):
    key: str
    overall: float | None
    per_variant: dict[str, float | None]

    @classmethod
    def from_dto(cls, point: MetricPointDTO) -> "MetricPointResponse":
        return MetricPointResponse(
            key=point.key,
            overall=point.overall,
            per_variant=point.per_variant,
        )


class ReportResponse(Struct):
    id: str
    experiment_id: str
    start_at: datetime
    end_at: datetime
    metrics: list[MetricPointResponse]

    @classmethod
    def from_dto(cls, dto: ReportResultDTO) -> "ReportResponse":
        return ReportResponse(
            id=dto.report_id,
            experiment_id=dto.experiment_id,
            start_at=dto.start_at,
            end_at=dto.end_at,
            metrics=[MetricPointResponse.from_dto(p) for p in dto.metrics],
        )


class MinimalReportResponse(Struct):
    id: str
    experiment_id: str
    start_at: datetime
    end_at: datetime

    @classmethod
    def from_report(cls, report: Report) -> "MinimalReportResponse":
        return MinimalReportResponse(
            id=report.id,
            experiment_id=report.experiment_id,
            start_at=report.window.start_at,
            end_at=report.window.end_at,
        )


class ReportsController(Controller):
    path = "/api/v1/reports"
    tags: Sequence[str] | None = ("Reports",)
    security = security_defs

    @post(
        path="/create",
        responses={
            201: success_spec("Created.", ReportResponse),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_report(
        self,
        data: CreateReportRequest,
        interactor: FromDishka[CreateReport],
        get_result: FromDishka[GetReportResult],
    ) -> ReportResponse:
        report = await interactor(
            CreateReportDTO(
                experiment_id=ExperimentId(data.experiment_id),
                start_at=data.start_at,
                end_at=data.end_at,
            ),
        )
        dto = await get_result(ReportId(report.id))
        return ReportResponse.from_dto(dto)

    @get(
        path="/{report_id:str}",
        responses={
            200: success_spec("Retrieved.", ReportResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_report(
        self,
        report_id: str,
        interactor: FromDishka[GetReportResult],
    ) -> ReportResponse:
        dto = await interactor(ReportId(report_id))
        return ReportResponse.from_dto(dto)

    @delete(
        path="/{report_id:str}",
        responses={
            204: success_spec("Deleted.", None),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def delete_report(
        self,
        report_id: str,
        interactor: FromDishka[DeleteReport],
    ) -> None:
        await interactor(ReportId(report_id))

    @get(
        path="/for-experiment/{experiment_id:str}",
        responses={
            200: success_spec("Retrieved.", list[MinimalReportResponse]),
            **RESPONSE_NOT_AUTHENTICATED,
        }
    )
    @inject
    async def list_for_experiment(
        self,
        experiment_id: str,
        interactor: FromDishka[ListReportsByExperiment]
    ) -> list[MinimalReportResponse]:
        reports = await interactor(ExperimentId(experiment_id))
        return list(map(MinimalReportResponse.from_report, reports))
