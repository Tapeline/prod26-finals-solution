from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class InvalidMetricDSLExpression(AppException):
    def __init__(self, message: str) -> None:
        self.text = f"Incorrect Metric DSL expression:\n{message}"
