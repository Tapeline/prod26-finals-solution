from typing import final

from alphabet.subject_events.application.interfaces import EventTypeCache
from alphabet.subject_events.domain.events import EventType


@final
class InMemoryEventTypeCache(EventTypeCache):
    def __init__(self) -> None:
        self._types = {}
        self._ready = False

    def get_event_type(self, event_type_id: str) -> EventType | None:
        return self._types.get(event_type_id, None)

    def place_event_types(self, event_types: list[EventType]) -> None:
        for event_type in event_types:
            self._types[event_type.id] = event_type

    def is_ready(self) -> bool:
        return self._ready

    def mark_ready(self) -> None:
        self._ready = True
