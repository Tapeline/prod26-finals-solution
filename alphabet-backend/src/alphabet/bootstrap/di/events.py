from dishka import Provider, Scope, provide, provide_all

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
    EventTelemetry,
    EventTypeCache,
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
from alphabet.subject_events.infrastructure.prometheus import (
    PrometheusEventTelemetry,
)
from alphabet.subject_events.infrastructure.valkey import (
    ValkeyEventDeduplicator,
)


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
    telemetry = provide(
        PrometheusEventTelemetry,
        provides=EventTelemetry,
        scope=Scope.APP,
    )
