from collections.abc import Collection
from pathlib import Path
from typing import final, override

from redis.asyncio import Redis

from alphabet.decisions.application import DecisionDataStore
from alphabet.decisions.domain import Decision, DecisionId
from alphabet.shared.commons import autoinit
from alphabet.shared.config import AppConfig


@final
@autoinit
class ValkeyDecisionDataStore(DecisionDataStore):
    client: Redis
    config: AppConfig

    def __post_init__(self) -> None:
        src_dir = Path(__file__).resolve().parent.parent.parent.parent
        self._record_script = self.client.register_script(
            (src_dir / "cooldown.lua").read_text(),
        )

    @override
    async def is_in_cooldown(self, subject_id: str) -> bool:
        key = f"cooldown:{subject_id}"
        return bool(await self.client.exists(key))

    @override
    async def save_decisions(
        self,
        subject_id: str,
        decisions: Collection[Decision],
    ) -> None:
        if not decisions:
            return
        async with self.client.pipeline() as pipe:
            await pipe.hset(  # type: ignore[misc]
                f"u:{subject_id}",
                mapping={
                    decision.flag_key: _dump_decision(decision)
                    for decision in decisions
                },
            )
            await pipe.expire(
                f"u:{subject_id}",
                self.config.store_stickiness_for_s,
            )
            await pipe.execute()

    @override
    async def load_existing_decisions(
        self,
        subject_id: str,
        flag_keys: list[str],
        experiment_ids: set[str],
    ) -> dict[str, Decision]:
        raw_decisions = await self.client.hmget(  # type: ignore[misc]
            f"u:{subject_id}",
            flag_keys,
        )
        decisions: dict[str, Decision] = {}
        for key, raw_decision in zip(flag_keys, raw_decisions, strict=True):
            if raw_decision:
                decision = _load_decision(raw_decision.decode())
                if decision.experiment_id in experiment_ids:
                    decisions[key] = decision
        return decisions

    @override
    async def record_experiment_assignments(
        self,
        subject_id: str,
        count: int,
    ) -> None:
        # this method is written by cursor
        if count <= 0:
            return
        await self._record_script(
            keys=[f"exp_count:{subject_id}", f"cooldown:{subject_id}"],
            args=[
                count,
                self.config.cooldown_experiment_threshold,
                self.config.cooldown_for_s,
            ],
        )


def _load_decision(decision_str: str) -> Decision:
    decision_id, flag_key, experiment_id, variant, value = decision_str.split(
        ";",
        maxsplit=4,
    )
    exp_id: str | None = experiment_id if experiment_id != "" else None
    return Decision(
        DecisionId(decision_id),
        flag_key,
        variant,
        value,
        exp_id,
    )


def _dump_decision(decision: Decision) -> str:
    exp_id = decision.experiment_id or ""
    return (
        f"{decision.id};{decision.flag_key};{exp_id};"
        f"{decision.variant_id};{decision.value}"
    )
