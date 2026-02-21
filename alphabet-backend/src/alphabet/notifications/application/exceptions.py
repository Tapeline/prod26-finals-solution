from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class RuleNotFound(AppException):
    text = "Rule not found"


@final
class FailedToSend(AppException):
    text = "Failed to send"
