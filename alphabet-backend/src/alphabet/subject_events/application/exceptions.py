from alphabet.shared.domain.exceptions import AppException


class EventTypeNotFound(AppException):
    text = "Event type not found"


class EventTypeAlreadyExists(AppException):
    text = "Event type already exists"
