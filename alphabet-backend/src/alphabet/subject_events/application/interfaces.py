from abc import abstractmethod
from typing import Protocol, Sequence

from alphabet.shared.application.pagination import Pagination
from alphabet.subject_events.domain.events import (
    EventType, EventTypeId,
    Event, DiscardedEvent,
)


class EventTypeRepository(Protocol):
    @abstractmethod
    async def create(self, event_type: EventType) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, event_type: EventType) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, event_type_id: EventTypeId) -> EventType | None:
        raise NotImplementedError

    @abstractmethod
    async def all(self, pagination: Pagination | None) -> list[EventType]:
        raise NotImplementedError


class EventTypeChangeNotifier(Protocol):
    @abstractmethod
    async def notify_event_type_created(self, event_type: EventType) -> None:
        raise NotImplementedError


class EventTypeCache(Protocol):
    @abstractmethod
    def get_event_type(self, event_type_id: str) -> EventType | None:
        raise NotImplementedError

    @abstractmethod
    def place_event_types(self, event_types: list[EventType]) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def mark_ready(self) -> None:
        raise NotImplementedError


class EventDeduplicator(Protocol):
    @abstractmethod
    async def query_processed_before(
        self, evt_ids: list[str]
    ) -> dict[str, bool]:
        raise NotImplementedError

    @abstractmethod
    async def mark_processed(self, evt_ids: Sequence[str]) -> None:
        raise NotImplementedError


class EventStore(Protocol):
    @abstractmethod
    async def save_batches(
        self,
        ok: list[Event],
        duplicates: list[Event],
        erroneous: list[DiscardedEvent]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def periodic_flush_routine(self) -> None:
        raise NotImplementedError
