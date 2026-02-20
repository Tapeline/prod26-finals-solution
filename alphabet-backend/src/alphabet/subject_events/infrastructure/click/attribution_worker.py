import asyncio
from typing import final

import structlog
from clickhouse_connect.driver import AsyncClient

from alphabet.shared.config import WorkersConfig


@final
class AttributionWorker:
    def __init__(self, click: AsyncClient, config: WorkersConfig) -> None:
        self.click = click
        self.is_running = False
        self.logger = structlog.get_logger("attribution_worker")
        self.interval = config.attribution_interval_s

    async def start(self) -> None:
        self.is_running = True
        self.logger.info("Attribution worker started")
        while self.is_running:
            try:
                await self._run_attribution_cycle()
            except Exception as exc:
                self.logger.exception(
                    "Attribution worker cycle failed",
                    exc_info=exc,
                )
            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        self.is_running = False

    async def _run_attribution_cycle(self) -> None:
        self.logger.info("Running attribution cycle")
        attribution_query = """
        INSERT INTO events
        SELECT
            child.id,
            child.decision_id,
            child.experiment_id,
            child.flag_key,
            child.subject_id,
            child.event_type,
            child.variant_id,
            child.issued_at,
            child.received_at,
            child.attributes,
            'accepted' as status,
            child.wants_event_type
        FROM (SELECT * FROM events FINAL) child
        INNER JOIN (
            SELECT decision_id, event_type
            FROM events FINAL
            WHERE status = 'accepted'
            GROUP BY decision_id, event_type
        ) parent ON child.decision_id = parent.decision_id
                 AND child.wants_event_type = parent.event_type
        WHERE child.status = 'waiting_attribution'
        """

        expiration_query = """
        INSERT INTO events
        SELECT
            id,
            decision_id,
            experiment_id,
            flag_key,
            subject_id,
            event_type,
            variant_id,
            issued_at,
            received_at,
            attributes,
            'attribution_despair' as status,
            wants_event_type
        FROM events FINAL
        WHERE status = 'waiting_attribution'
          AND received_at < now64(3) - INTERVAL 7 DAY
        """

        await self.click.command(attribution_query)
        await self.click.command(expiration_query)

        self.logger.debug("Attribution cycle completed successfully")
