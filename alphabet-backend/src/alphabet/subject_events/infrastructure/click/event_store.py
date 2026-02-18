import asyncio
import json
from datetime import datetime
from typing import final, Final

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
        self._ok_buf = []
        self._err_buf = []
        self._dup_buf = []
        self._write_lock = asyncio.Lock()
        self._last_flush = datetime.now()
        self.click = click
        self.time = time

    @property
    def _accumulated(self) -> int:
        return len(self._ok_buf) + len(self._err_buf) + len(self._dup_buf)

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
                await self._flush_no_lock()

    async def _periodic_flush(self):
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL_SECONDS)
            async with self._write_lock:
                await self._flush_no_lock()

    async def _flush_no_lock(self):
        if self._ok_buf:
            await self.click.insert(
                'events', [
                    [
                        str(e.id), e.decision_id, str(e.event_type),
                        e.variant_id,
                        e.issued_at, e.received_at, json.dumps(e.attributes),
                        e.status.value,
                        str(e.wants_event_type) if e.wants_event_type else None
                    ] for e in self._ok_buf
                ], column_names=[
                    'id', 'decision_id', 'event_type', 'variant_id',
                    'issued_at', 'received_at', 'attributes', 'status',
                    'wants_event_type'
                ]
            )
            self._ok_buf.clear()
        if self._err_buf:
            await self.click.insert(
                'discarded_events', [
                    [
                        str(e.id), e.decision_id, e.event_type_id,
                        e.issued_at, e.received_at, json.dumps(e.attributes),
                        e.discard_reason
                    ] for e in self._err_buf
                ], column_names=[
                    'id', 'decision_id', 'event_type_id',
                    'issued_at', 'received_at', 'attributes', 'discard_reason'
                ]
            )
            self._err_buf.clear()
        if self._dup_buf:
            await self.click.insert(
                'duplicate_events', [
                    [
                        str(e.id), e.decision_id, str(e.event_type),
                        e.variant_id,
                        e.issued_at, e.received_at, json.dumps(e.attributes),
                        e.status.value,
                        str(e.wants_event_type) if e.wants_event_type else None
                    ] for e in self._dup_buf
                ], column_names=[
                    'id', 'decision_id', 'event_type', 'variant_id',
                    'issued_at', 'received_at', 'attributes', 'status',
                    'wants_event_type'
                ]
            )
            self._dup_buf.clear()
        self._last_flush = self.time.now()
