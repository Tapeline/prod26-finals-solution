from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class GuardRuleNotFound(AppException):
    text = "Guardrail rule not found"
