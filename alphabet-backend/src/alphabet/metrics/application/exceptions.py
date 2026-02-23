from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class ExperimentForReportNotFound(AppException):
    text = "Experiment for report not found"
