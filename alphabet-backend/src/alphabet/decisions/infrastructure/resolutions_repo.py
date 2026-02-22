import asyncio
from typing import final, override

from clickhouse_connect.driver import AsyncClient
from structlog import getLogger

from alphabet.decisions.application import ResolutionRepository
from alphabet.decisions.domain import ConflictResolution
from alphabet.experiments.domain.experiment import (
    ConflictDomain,
    ConflictPolicy,
    ExperimentId,
)
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.config import Config


@final
class ClickHouseResolutionRepository(ResolutionRepository):
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
        self._buf: list[ConflictResolution] = []
        self._write_lock = asyncio.Lock()
        self._batch_size = config.conflict_buffer.size
        self._flush_interval = config.conflict_buffer.force_flush_interval_s
        self._last_flush = time.now()

    @override
    async def save_resolutions(
        self,
        resolutions: list[ConflictResolution],
    ) -> None:
        if not resolutions:
            return
        async with self._write_lock:
            self._buf.extend(resolutions)
            if len(self._buf) >= self._batch_size:
                self.logger.info(
                    "Flushing conflict resolutions from threshold",
                    buf_len=len(self._buf),
                )
                await self._flush_no_lock()

    @override
    async def count_conflicts_by_domain(
        self,
        domain: ConflictDomain,
    ) -> dict[ExperimentId, int]:
        rows = await self.click.query(
            """
            SELECT
                experiment_id,
                count() as cnt
            FROM conflict_resolutions
            WHERE domain = %(domain)s
            GROUP BY experiment_id
            """,
            parameters={"domain": domain.value},
        )
        return {
            ExperimentId(exp_id): count for exp_id, count in rows.result_rows
        }

    @override
    async def count_conflicts_by_experiment(
        self,
        experiment_id: str,
    ) -> tuple[dict[ConflictPolicy, int], dict[ConflictPolicy, int]]:
        rows = await self.click.query(
            """
            SELECT
                policy,
                was_applied,
                count() as cnt
            FROM conflict_resolutions
            WHERE experiment_id = %(exp_id)s
            GROUP BY policy, was_applied
            """,
            parameters={"exp_id": experiment_id},
        )
        wins: dict[ConflictPolicy, int] = {}
        losses: dict[ConflictPolicy, int] = {}
        for policy_str, was_applied, count in rows.result_rows:
            try:
                policy = ConflictPolicy(policy_str)
            except ValueError:
                self.logger.warning("Unknown policy in DB", policy=policy_str)
                continue
            if was_applied == 1:
                wins[policy] = count
            else:
                losses[policy] = count
        return wins, losses

    @override
    async def periodic_flush_routine(self) -> None:
        self.logger.info("Starting conflicts flush routine")
        while True:
            await asyncio.sleep(self._flush_interval)
            try:
                async with self._write_lock:
                    self.logger.info(
                        "Flushing conflict resolutions from routine",
                        to_write=len(self._buf),
                    )
                    await self._flush_no_lock()
            except Exception as exc:
                self.logger.exception(
                    "Exception while flushing conflicts", exc=exc,
                )

    async def _flush_no_lock(self) -> None:
        if not self._buf:
            return
        now = self.time.now()
        await self.click.insert(
            table="conflict_resolutions",
            data=[
                [
                    now,
                    resolution.domain,
                    resolution.experiment_id,
                    resolution.policy.value,
                    1 if resolution.experiment_applied else 0,
                ]
                for resolution in self._buf
            ],
            column_names=[
                "timestamp",
                "domain",
                "experiment_id",
                "policy",
                "was_applied",
            ],
        )
        self._buf.clear()
        self._last_flush = now
