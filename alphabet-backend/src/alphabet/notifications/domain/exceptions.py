from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class InvalidConnectionString(AppException):
    text = "Connection string must satisfy DSL spec"


@final
class InvalidRatelimit(AppException):
    text = "Rate limit must be > 0"


@final
class InvalidTrigger(AppException):
    text = "Trigger must satisfy DSL spec"
