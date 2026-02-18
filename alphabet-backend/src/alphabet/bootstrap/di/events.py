from dishka import AnyOf, Provider, Scope, provide, provide_all

from alphabet.subject_events.application.interactors import (
    ArchiveEventType,
    CreateEventType,
    ReadAllEventTypes,
    ReadEventType,
    ReceiveEvents,
    UpdateEventType,
    WarmUpEventTypes,
)
from alphabet.subject_events.application.interfaces import (
    EventDeduplicator,
    EventStore,
    EventTypeCache,
    EventTypeChangeNotifier,
    EventTypeRepository,
)
from alphabet.subject_events.infrastructure.click.event_store import (
    ClickHouseEventStore,
)
from alphabet.subject_events.infrastructure.in_memory import (
    InMemoryEventTypeCache,
)
from alphabet.subject_events.infrastructure.postgres.event_types_repo import (
    SqlEventTypeRepository,
)
from alphabet.subject_events.infrastructure.valkey import (
    ValkeyEventDeduplicator,
)
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.infrastructure.transaction import SqlTransactionManager
from clickhouse_connect.driver import AsyncClient


class EventsDIProvider(Provider):
    interactors = provide_all(
        CreateEventType,
        UpdateEventType,
        ArchiveEventType,
        ReadEventType,
        ReadAllEventTypes,
        ReceiveEvents,
        WarmUpEventTypes,
        scope=Scope.REQUEST,
    )

    event_types_repo = provide(
        SqlEventTypeRepository,
        provides=EventTypeRepository,
        scope=Scope.REQUEST,
    )

    event_type_cache = provide(
        InMemoryEventTypeCache,
        provides=EventTypeCache,
        scope=Scope.APP,
    )

    event_store = provide(
        ClickHouseEventStore,
        provides=EventStore,
        scope=Scope.APP,
    )

    event_deduplicator = provide(
        ValkeyEventDeduplicator,
        provides=EventDeduplicator,
        scope=Scope.REQUEST,
    )
