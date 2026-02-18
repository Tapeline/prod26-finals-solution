from operator import attrgetter
from typing import Any, overload, override

from sqlalchemy import Row, insert, select, update
from sqlalchemy.exc import IntegrityError

from alphabet.experiments.infrastructure.tables import (
    flags,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.commons import maybe_map
from alphabet.shared.infrastructure.transaction import SqlTransactionManager
from alphabet.subject_events.application.exceptions import (
    EventTypeAlreadyExists,
)
from alphabet.subject_events.application.interfaces import EventTypeRepository
from alphabet.subject_events.domain.events import (
    EventSchema,
    EventType,
    EventTypeId,
)
from alphabet.subject_events.infrastructure.postgres.tables import event_types


class SqlEventTypeRepository(EventTypeRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def get_by_id(self, event_type_id: EventTypeId) -> EventType | None:
        result = await self.session.execute(
            select(event_types).where(event_types.c.id == event_type_id.value),
        )
        return _row_to_event_type(result.first())

    @override
    async def create(self, event_type: EventType) -> None:
        try:
            await self.session.execute(
                insert(event_types).values(
                    id=event_type.id.value,
                    name=event_type.name,
                    schema=event_type.schema.json,
                    requires_attribution=maybe_map(
                        event_type.requires_attribution,
                        attrgetter("value"),
                    ),
                    is_archived=event_type.is_archived,
                ),
            )
        except IntegrityError as exc:
            raise EventTypeAlreadyExists from exc

    @override
    async def save(self, event_type: EventType) -> None:
        await self.session.execute(
            update(event_types)
            .where(event_types.c.id == event_type.id.value)
            .values(
                id=event_type.id.value,
                name=event_type.name,
                schema=event_type.schema.json,
                requires_attribution=maybe_map(
                    event_type.requires_attribution,
                    attrgetter("value"),
                ),
                is_archived=event_type.is_archived,
            ),
        )

    @override
    async def all(self, pagination: Pagination | None) -> list[EventType]:
        if pagination is None:
            result = await self.session.execute(select(event_types))
        else:
            result = await self.session.execute(
                select(flags)
                .limit(pagination.limit)
                .offset(pagination.offset),
            )
        return list(map(_row_to_event_type, result.all()))


@overload
def _row_to_event_type(row: Row[Any]) -> EventType: ...


@overload
def _row_to_event_type(row: None) -> None: ...


def _row_to_event_type(row: Row[Any] | None) -> EventType | None:
    if not row:
        return None
    return EventType(
        id=EventTypeId(row.id),
        name=row.name,
        schema=EventSchema(row.schema),
        requires_attribution=maybe_map(row.requires_attribution, EventTypeId),
        is_archived=row.is_archived,
    )
