from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class MetricAlreadyExists(AppException):
    text = "Metric with this id already exists"


@final
class NoSuchMetric(AppException):
    text = "No such metric"


@final
class NoSuchReport(AppException):
    text = "No such report"


@final
class InvalidMetricKey(AppException):
    text = "Metric key should be [A-Za-z0-9_-]+"


@final
class InvalidReportWindow(AppException):
    text = "Invalid report window"
