import asyncio
import json
from datetime import datetime
from logging import getLogger
from typing import final, Final, override

from clickhouse_connect.driver import AsyncClient

from alphabet.shared.application.time import TimeProvider
from alphabet.subject_events.application.interfaces import EventStore
from alphabet.subject_events.domain.events import Event, DiscardedEvent

# TODO: maybe put into config?
_BUFFER_SIZE_THRESHOLD: Final = 2000
_FLUSH_INTERVAL_SECONDS: Final = 5


@final
class ClickHouseEventStore(EventStore):
    def __init__(self, click: AsyncClient, time: TimeProvider):
        self._ok_buf: list[Event] = []
        self._err_buf: list[DiscardedEvent] = []
        self._dup_buf: list[Event] = []
        self._write_lock = asyncio.Lock()
        self._last_flush = datetime.now()
        self.click = click
        self.time = time
        self.logger = getLogger(__name__)

    @property
    def _accumulated(self) -> int:
        return len(self._ok_buf) + len(self._err_buf) + len(self._dup_buf)

    @override
    async def save_batches(
        self,
        ok: list[Event],
        duplicates: list[Event],
        erroneous: list[DiscardedEvent]
    ) -> None:
        async with self._write_lock:
            self._ok_buf.extend(ok)
            self._dup_buf.extend(duplicates)
            self._err_buf.extend(erroneous)
            if self._accumulated >= _BUFFER_SIZE_THRESHOLD:
                self.logger.info("Flushing events from threshold")
                await self._flush_no_lock()

    @override
    async def periodic_flush_routine(self) -> None:
        self.logger.info("Starting event flush routine")
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL_SECONDS)
            self.logger.info("Flushing events from routine")
            async with self._write_lock:
                await self._flush_no_lock()

    async def _flush_no_lock(self) -> None:
        # TODO: clean this mess
        if self._ok_buf:
            await self.click.insert(
                "events", [
                    [
                        str(e.id), e.decision_id, e.event_type.value,
                        e.variant_id,
                        e.issued_at, e.received_at, json.dumps(e.attributes),
                        e.status.value,
                        e.wants_event_type.value if e.wants_event_type else None
                    ] for e in self._ok_buf
                ], column_names=[
                    "id", "decision_id", "event_type", "variant_id",
                    "issued_at", "received_at", "attributes", "status",
                    "wants_event_type"
                ]
            )
            self._ok_buf.clear()
        if self._err_buf:
            await self.click.insert(
                "discarded_events", [
                    [
                        str(e.id), e.decision_id, e.event_type_id,
                        e.issued_at, e.received_at, json.dumps(e.attributes),
                        e.discard_reason
                    ] for e in self._err_buf
                ], column_names=[
                    "id", "decision_id", "event_type_id",
                    "issued_at", "received_at", "attributes", "discard_reason"
                ]
            )
            self._err_buf.clear()
        if self._dup_buf:
            await self.click.insert(
                "duplicate_events", [
                    [
                        str(e.id), e.decision_id, e.event_type.value,
                        e.variant_id,
                        e.issued_at, e.received_at, json.dumps(e.attributes),
                        e.status.value,
                        e.wants_event_type.value if e.wants_event_type else None
                    ] for e in self._dup_buf
                ], column_names=[
                    "id", "decision_id", "event_type", "variant_id",
                    "issued_at", "received_at", "attributes", "status",
                    "wants_event_type"
                ]
            )
            self._dup_buf.clear()
        self._last_flush = self.time.now()
