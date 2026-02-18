import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Final, NewType, final

import jsonschema_rs

from alphabet.shared.commons import entity, value_object
from alphabet.subject_events.domain.exceptions import (
    InvalidEventTypeId,
    InvalidJsonSchema,
)

_EVT_TYPE_ID_RE: Final = re.compile("[A-Za-z0-9_-]+")


@final
@value_object
class EventTypeId:
    value: str

    def __post_init__(self) -> None:
        if not _EVT_TYPE_ID_RE.fullmatch(self.value):
            raise InvalidEventTypeId


@final
class EventSchema:
    __slots__ = ("json", "value")

    value: jsonschema_rs.Validator
    json: dict[str, Any]

    def __init__(self, schema: dict[str, Any]) -> None:
        try:
            self.json = schema
            self.value = jsonschema_rs.validator_for(schema)
        except ValueError as exc:
            raise InvalidJsonSchema from exc


@final
@entity
class EventType:
    id: EventTypeId
    name: str
    schema: EventSchema
    requires_attribution: EventTypeId | None
    is_archived: bool


EventId = NewType("EventId", str)


@final
class EventStatus(StrEnum):
    WAITING_ATTRIBUTION = "waiting_attribution"
    ACCEPTED = "accepted"
    ATTRIBUTION_DESPAIR = "attribution_despair"
    # funny lil name to mark that attribution will never happen :(


@final
@entity
class Event:
    id: EventId
    decision_id: str
    event_type: EventTypeId
    variant_id: str
    issued_at: datetime
    received_at: datetime
    attributes: dict[str, Any]
    status: EventStatus
    wants_event_type: EventTypeId | None


@final
@entity
class DiscardedEvent:
    id: EventId
    decision_id: str
    event_type_id: str
    issued_at: datetime
    received_at: datetime
    attributes: dict[str, Any]
    discard_reason: str
