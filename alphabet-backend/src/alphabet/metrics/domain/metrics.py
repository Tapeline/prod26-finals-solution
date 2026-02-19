import re
from datetime import datetime
from typing import Final, NewType, final

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.domain.exceptions import (
    InvalidMetricKey,
    InvalidReportWindow,
)
from alphabet.shared.commons import entity, value_object, dto

ReportId = NewType("ReportId", str)

_METRIC_KEY_RE: Final = re.compile("[A-Za-z0-9_-]+")


@value_object
@final
class SQLFragment:
    select: str
    table: str
    where: str


@final
@value_object
class MetricKey:
    value: str

    def __post_init__(self) -> None:
        if not _METRIC_KEY_RE.fullmatch(self.value):
            raise InvalidMetricKey


@final
@entity
class Metric:
    key: MetricKey
    expression: str
    compiled_expression: tuple[SQLFragment, SQLFragment | None]


@final
@value_object
class ReportWindow:
    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        if self.start_at >= self.end_at:
            raise InvalidReportWindow


@final
@entity
class Report:
    id: ReportId
    experiment_id: ExperimentId
    window: ReportWindow
