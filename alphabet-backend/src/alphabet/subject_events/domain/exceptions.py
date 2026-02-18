from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class InvalidEventTypeId(AppException):
    text = "Invalid event type id"


@final
class InvalidJsonSchema(AppException):
    text = "Invalid JSON schema"
