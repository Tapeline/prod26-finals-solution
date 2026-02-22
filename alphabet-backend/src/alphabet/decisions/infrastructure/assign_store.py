import asyncio
from datetime import datetime
from typing import final, override

from clickhouse_connect.driver import AsyncClient
from structlog import getLogger

from alphabet.decisions.application import (
    AssignmentStore,
)
from alphabet.decisions.domain import Decision
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.config import Config


@final
class ClickHouseAssignmentStore(AssignmentStore):
    def __init__(
        self,
        click: AsyncClient,
        time: TimeProvider,
        config: Config,
    ) -> None:
        self.click = click
        self.time = time
        self.config = config
        self.logger = getLogger(__name__)
        self._buf: list[tuple[Decision, datetime, str]] = []
        self._write_lock = asyncio.Lock()
        self._batch_size = config.assignment_buffer.size
        self._flush_interval = config.assignment_buffer.force_flush_interval_s

    @override
    async def save_assignments(
        self,
        decisions: list[Decision],
        decided_at: datetime,
        subject_id: str,
    ) -> None:
        if not decisions:
            return
        async with self._write_lock:
            self._buf.extend(
                (decision, decided_at, subject_id) for decision in decisions
            )
            if len(self._buf) >= self._batch_size:
                self.logger.info("Flushing assignments from threshold")
                await self._flush_no_lock()

    @override
    async def get_variant_distribution(
        self,
        experiment_id: str,
    ) -> dict[str, int]:
        rows = await self.click.query(
            """
            SELECT
                variant_id,
                count() as cnt
            FROM variant_assignments
            WHERE experiment_id = %(exp_id)s
            GROUP BY variant_id
            """,
            parameters={"exp_id": experiment_id},
        )
        return {variant: count for variant, count in
            rows.result_rows}  # noqa: C416

    @override
    async def periodic_flush_routine(self) -> None:
        self.logger.info("Starting assignment flush routine")
        while True:
            await asyncio.sleep(self._flush_interval)
            try:
                async with self._write_lock:
                    self.logger.info(
                        "Flushing assignments from routine",
                        to_write=len(self._buf),
                    )
                    await self._flush_no_lock()
            except Exception as exc:
                self.logger.exception(
                    "Exception while flushing assignments", exc=exc
                )

    async def _flush_no_lock(self) -> None:
        if not self._buf:
            return
        await self.click.insert(
            "variant_assignments",
            data=[
                [
                    int(decided_at.timestamp()),
                    decision.experiment_id,
                    decision.variant_id,
                    subject_id,
                    decision.flag_key,
                ]
                for decision, decided_at, subject_id in self._buf
            ],
            column_names=[
                "timestamp",
                "experiment_id",
                "variant_id",
                "subject_id",
                "flag_key",
            ],
        )
        self._buf.clear()
