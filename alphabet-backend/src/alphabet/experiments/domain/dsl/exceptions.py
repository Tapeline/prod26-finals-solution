from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class InvalidTargetDSLExpression(AppException):
    def __init__(self, message: str) -> None:
        self.text = f"Incorrect DSL expression:\n{message}"
