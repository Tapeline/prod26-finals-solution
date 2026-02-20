from datetime import datetime
from typing import Any, Final, Literal, cast, final

import jsonschema_rs
from structlog import getLogger

from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import UserReader, require_user_with_role
from alphabet.shared.commons import dto, interactor
from alphabet.shared.domain.user import Role
from alphabet.subject_events.application.exceptions import EventTypeNotFound
from alphabet.subject_events.application.interfaces import (
    EventDeduplicator,
    EventStore,
    EventTypeCache,
    EventTypeChangeNotifier,
    EventTypeRepository,
)
from alphabet.subject_events.domain.events import (
    DiscardedEvent,
    Event,
    EventId,
    EventSchema,
    EventStatus,
    EventType,
    EventTypeId,
)

logger = getLogger(__name__)


@final
@dto
class CreateEventTypeDTO:
    id: EventTypeId
    name: str
    schema: EventSchema
    requires_attribution: EventTypeId | None


@final
@dto
class UpdateEventTypeDTO:
    new_name: str


@final
@interactor
class CreateEventType:
    event_types: EventTypeRepository
    idp: UserIdProvider
    tx: TransactionManager
    user_reader: UserReader
    notifier: EventTypeChangeNotifier

    async def __call__(self, dto: CreateEventTypeDTO) -> EventType:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            event_type = EventType(
                dto.id,
                dto.name,
                dto.schema,
                dto.requires_attribution,
                is_archived=False,
            )
            await self.event_types.create(event_type)
        await self.notifier.notify_event_type_created(event_type)
        return event_type


@final
@interactor
class UpdateEventType:
    event_types: EventTypeRepository
    idp: UserIdProvider
    tx: TransactionManager
    user_reader: UserReader

    async def __call__(
        self,
        target: EventTypeId,
        dto: UpdateEventTypeDTO,
    ) -> EventType:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            event_type = await self.event_types.get_by_id(target)
            if not event_type:
                raise EventTypeNotFound
            event_type.name = dto.new_name
            await self.event_types.save(event_type)
            return event_type


@final
@interactor
class ArchiveEventType:
    event_types: EventTypeRepository
    idp: UserIdProvider
    tx: TransactionManager
    user_reader: UserReader
    notifier: EventTypeChangeNotifier

    async def __call__(self, target: EventTypeId) -> EventType:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN, Role.EXPERIMENTER})
            event_type = await self.event_types.get_by_id(target)
            if not event_type:
                raise EventTypeNotFound
            if event_type.is_archived:
                return event_type
            event_type.is_archived = True
            await self.event_types.save(event_type)
            return event_type


@final
@interactor
class ReadEventType:
    event_types: EventTypeRepository
    tx: TransactionManager

    async def __call__(self, target: EventTypeId) -> EventType:
        async with self.tx:
            event_type = await self.event_types.get_by_id(target)
            if not event_type:
                raise EventTypeNotFound
            return event_type


@final
@interactor
class ReadAllEventTypes:
    event_types: EventTypeRepository
    tx: TransactionManager

    async def __call__(self, pagination: Pagination) -> list[EventType]:
        async with self.tx:
            return await self.event_types.all(pagination)


@final
@dto
class IncomingEventDTO:
    event_id: str
    event_type: str
    decision_id: str
    payload: dict[str, Any]
    issued_at: datetime

    @property
    def variant_id(self) -> str:
        return self.decision_id.split(":", maxsplit=3)[3]

    @property
    def experiment_id(self) -> str:
        return self.decision_id.split(":", maxsplit=3)[0]

    @property
    def flag_key(self) -> str:
        return self.decision_id.split(":", maxsplit=3)[1]

    @property
    def subject_id(self) -> str:
        return self.decision_id.split(":", maxsplit=3)[2]


@final
@dto
class IncomingEventsResult:
    ok_count: int
    duplicate_count: int
    errors: dict[int, str]


_PROCESSED_ERROR: Final[Literal[2]] = 2
_PROCESSED_DUPLICATE: Final[Literal[1]] = 1
_PROCESSED_OK: Final[Literal[0]] = 0


@final
@interactor
class ReceiveEvents:
    event_store: EventStore
    event_type_cache: EventTypeCache
    event_deduplicator: EventDeduplicator
    time: TimeProvider

    async def __call__(
        self,
        events: list[IncomingEventDTO],
    ) -> IncomingEventsResult:
        errors: dict[int, str] = {}
        duplicates: list[Event] = []
        erroneous: list[DiscardedEvent] = []
        ok: list[Event] = []
        current_time = self.time.now()
        processed = []
        processed_earlier = (
            await self.event_deduplicator.query_processed_before(
                [event.event_id for event in events],
            )
        )
        for i, event_dto in enumerate(events):
            result, event = self._process_event(
                event_dto,
                current_time,
                processed_earlier,
            )
            if result == _PROCESSED_OK:
                ok.append(cast(Event, event))
            elif result == _PROCESSED_DUPLICATE:
                duplicates.append(cast(Event, event))
            elif result == _PROCESSED_ERROR:
                erroneous.append(cast(DiscardedEvent, event))
                errors[i] = cast(DiscardedEvent, event).discard_reason
            processed.append(event.id)
        await self.event_store.save_batches(ok, duplicates, erroneous)
        await self.event_deduplicator.mark_processed(processed)
        return IncomingEventsResult(
            ok_count=len(ok),
            duplicate_count=len(duplicates),
            errors=errors,
        )

    def _process_event(
        self,
        event: IncomingEventDTO,
        current_time: datetime,
        processed_earlier: dict[str, bool],
    ) -> tuple[Literal[0, 1], Event] | tuple[Literal[2], DiscardedEvent]:
        evt_type = self.event_type_cache.get_event_type(event.event_type)
        if not evt_type:
            return (
                _PROCESSED_ERROR,
                _to_discarded(event, current_time, "no_such_type"),
            )
        try:
            evt_type.schema.value.validate(event.payload)
        except jsonschema_rs.ValidationError:
            return (
                _PROCESSED_ERROR,
                _to_discarded(event, current_time, "bad_payload"),
            )
        if processed_earlier[event.event_id]:
            return (
                _PROCESSED_DUPLICATE,
                _to_event(evt_type, event, current_time),
            )
        return (_PROCESSED_OK, _to_event(evt_type, event, current_time))


def _to_discarded(
    dto: IncomingEventDTO,
    current_time: datetime,
    reason: str,
) -> DiscardedEvent:
    return DiscardedEvent(
        id=EventId(dto.event_id),
        decision_id=dto.decision_id,
        issued_at=dto.issued_at,
        received_at=current_time,
        attributes=dto.payload,
        discard_reason=reason,
        event_type_id=dto.event_type,
        experiment_id=dto.experiment_id,
        subject_id=dto.subject_id,
        flag_key=dto.flag_key,
    )


def _to_event(
    event_type: EventType,
    dto: IncomingEventDTO,
    current_time: datetime,
) -> Event:
    return Event(
        id=EventId(dto.event_id),
        event_type=EventTypeId(dto.event_type),
        decision_id=dto.decision_id,
        issued_at=dto.issued_at,
        received_at=current_time,
        attributes=dto.payload,
        variant_id=dto.variant_id,
        status=EventStatus.WAITING_ATTRIBUTION
        if event_type.requires_attribution is not None
        else EventStatus.ACCEPTED,
        wants_event_type=event_type.requires_attribution,
        experiment_id=dto.experiment_id,
        subject_id=dto.subject_id,
        flag_key=dto.flag_key,
    )


@final
@interactor
class WarmUpEventTypes:
    event_type_cache: EventTypeCache
    event_types: EventTypeRepository

    async def __call__(self) -> None:
        logger.info("Warming up event types cache")
        event_types = await self.event_types.all(pagination=None)
        self.event_type_cache.place_event_types(event_types)
        self.event_type_cache.mark_ready()
        logger.info(
            "Event types cache warmed up for %s entries",
            len(event_types),
        )
        logger.info("Event types cache is ready")
