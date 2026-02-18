from collections.abc import Sequence
from typing import final, override

from redis.asyncio import Redis

from alphabet.shared.commons import autoinit
from alphabet.shared.config import AppConfig
from alphabet.subject_events.application.interfaces import EventDeduplicator


@final
@autoinit
class ValkeyEventDeduplicator(EventDeduplicator):
    client: Redis
    config: AppConfig

    @override
    async def query_processed_before(
        self,
        evt_ids: list[str],
    ) -> dict[str, bool]:
        if not evt_ids:
            return {}
        keys = [f"dedupevt-{evt_id}" for evt_id in evt_ids]
        values = await self.client.mget(keys)
        return {
            evt_id: val is not None
            for evt_id, val in zip(evt_ids, values, strict=True)
        }

    @override
    async def mark_processed(self, evt_ids: Sequence[str]) -> None:
        if not evt_ids:
            return
        async with self.client.pipeline() as pipe:
            for evt_id in evt_ids:
                await pipe.set(
                    f"dedupevt-{evt_id}",
                    b"1",
                    ex=self.config.event_deduplication_ttl_s,
                )
            await pipe.execute()
