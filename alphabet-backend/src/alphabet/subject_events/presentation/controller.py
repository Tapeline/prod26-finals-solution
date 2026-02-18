from collections.abc import Sequence
from datetime import datetime
from typing import Any

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post
from msgspec import Struct

from alphabet.shared.application.pagination import Pagination
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    RESPONSE_NOT_FOUND,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs
from alphabet.subject_events.application.interactors import (
    ArchiveEventType,
    CreateEventType,
    CreateEventTypeDTO,
    IncomingEventDTO,
    IncomingEventsResult,
    ReadAllEventTypes,
    ReadEventType,
    ReceiveEvents,
    UpdateEventType,
    UpdateEventTypeDTO,
)
from alphabet.subject_events.domain.events import (
    EventSchema,
    EventType,
    EventTypeId,
)


class CreateEventTypeRequest(Struct):
    id: str
    name: str
    schema: dict[str, Any]
    requires_attribution: str | None = None


class UpdateEventTypeRequest(Struct):
    new_name: str


class EventTypeResponse(Struct):
    id: str
    name: str
    schema: dict[str, Any]
    requires_attribution: str | None
    is_archived: bool

    @staticmethod
    def from_event_type(event_type: EventType) -> "EventTypeResponse":
        return EventTypeResponse(
            id=event_type.id.value,
            name=event_type.name,
            schema=event_type.schema.json,
            requires_attribution=event_type.requires_attribution.value
            if event_type.requires_attribution
            else None,
            is_archived=event_type.is_archived,
        )


class IncomingEventSchema(Struct):
    event_id: str
    event_type: str
    decision_id: str
    payload: dict[str, Any]
    issued_at: datetime


class ReceiveEventsRequest(Struct):
    events: list[IncomingEventSchema]


class ReceiveEventsResponse(Struct):
    ok_count: int
    duplicate_count: int
    errors: dict[int, str]

    @staticmethod
    def from_result(result: IncomingEventsResult) -> "ReceiveEventsResponse":
        return ReceiveEventsResponse(
            ok_count=result.ok_count,
            duplicate_count=result.duplicate_count,
            errors=result.errors,
        )


class EventsController(Controller):
    path = "/api/v1/events"
    tags: Sequence[str] | None = ("Events",)
    security = security_defs

    @post(
        path="/types/create",
        responses={
            201: success_spec("Created.", EventTypeResponse),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_event_type(
        self,
        data: CreateEventTypeRequest,
        interactor: FromDishka[CreateEventType],
    ) -> EventTypeResponse:
        event_type = await interactor(
            CreateEventTypeDTO(
                id=EventTypeId(data.id),
                name=data.name,
                schema=EventSchema(data.schema),
                requires_attribution=EventTypeId(data.requires_attribution)
                if data.requires_attribution
                else None,
            ),
        )
        return EventTypeResponse.from_event_type(event_type)

    @get(
        path="/types",
        responses={
            200: success_spec("Retrieved.", list[EventTypeResponse]),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_all_event_types(
        self,
        interactor: FromDishka[ReadAllEventTypes],
        limit: int = 50,
        offset: int = 0,
    ) -> list[EventTypeResponse]:
        event_types = await interactor(Pagination(limit, offset))
        return list(map(EventTypeResponse.from_event_type, event_types))

    @get(
        path="/types/{event_type_id:str}",
        responses={
            200: success_spec("Retrieved.", EventTypeResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_event_type(
        self,
        event_type_id: str,
        interactor: FromDishka[ReadEventType],
    ) -> EventTypeResponse:
        event_type = await interactor(EventTypeId(event_type_id))
        return EventTypeResponse.from_event_type(event_type)

    @patch(
        path="/types/{event_type_id:str}",
        responses={
            200: success_spec("Updated.", EventTypeResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def update_event_type(
        self,
        event_type_id: str,
        data: UpdateEventTypeRequest,
        interactor: FromDishka[UpdateEventType],
    ) -> EventTypeResponse:
        event_type = await interactor(
            EventTypeId(event_type_id),
            UpdateEventTypeDTO(new_name=data.new_name),
        )
        return EventTypeResponse.from_event_type(event_type)

    @patch(
        path="/types/{event_type_id:str}/archive",
        responses={
            200: success_spec("Archived.", EventTypeResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def archive_event_type(
        self,
        event_type_id: str,
        interactor: FromDishka[ArchiveEventType],
    ) -> EventTypeResponse:
        event_type = await interactor(EventTypeId(event_type_id))
        return EventTypeResponse.from_event_type(event_type)

    @post(
        path="/receive",
        responses={
            200: success_spec("Events received.", ReceiveEventsResponse),
        },
        security=None,
        status_code=200,
    )
    @inject
    async def receive_events(
        self,
        data: ReceiveEventsRequest,
        interactor: FromDishka[ReceiveEvents],
    ) -> ReceiveEventsResponse:
        events_dto = [
            IncomingEventDTO(
                event_id=event.event_id,
                event_type=event.event_type,
                decision_id=event.decision_id,
                payload=event.payload,
                issued_at=event.issued_at,
            )
            for event in data.events
        ]
        result = await interactor(events_dto)
        return ReceiveEventsResponse.from_result(result)
