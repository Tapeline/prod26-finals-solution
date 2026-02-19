from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class ReportWindowInvalid(AppException):
    text = "Report window is invalid"


@final
class ExperimentForReportNotFound(AppException):
    text = "Experiment for report not found"


@final
class MetricNotInExperiment(AppException):
    text = "Metric is not configured for this experiment"

