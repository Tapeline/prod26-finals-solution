from pathlib import Path

from typing import Collection, final, override

from redis.asyncio import Redis

from alphabet.decisions.application import DecisionDataStore
from alphabet.decisions.domain import Decision, DecisionId
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.commons import autoinit
from alphabet.shared.config import AppConfig


@final
@autoinit
class ValkeyDecisionDataStore(DecisionDataStore):
    client: Redis
    time: TimeProvider
    config: AppConfig

    def __post_init__(self) -> None:
        # suggested by gemini, let's hope it's good :/
        self._cooldown_script = self.client.register_script(
            Path("src/cooldown.lua").read_text()
        )

    @override
    async def is_in_cooldown_or_set_if_needed(self, subject_id: str) -> bool:
        # suggested by gemini, let's hope it's good :/
        result = await self._cooldown_script(
            keys=[f"cooldown:{subject_id}", f"last-cycle:{subject_id}"],
            args=[
                int(self.time.now_unix_timestamp()),
                self.config.cooldown_after_s,
                self.config.cooldown_for_s
            ]
        )
        return bool(result)

    @override
    async def save_decisions(
        self,
        subject_id: str,
        decisions: Collection[Decision]
    ) -> None:
        if not decisions:
            return
        async with self.client.pipeline() as pipe:
            await pipe.hset(  # type: ignore[misc]
                f"u:{subject_id}",
                mapping={
                    decision.flag_key: _dump_decision(decision)
                    for decision in decisions
                }
            )
            await pipe.expire(
                f"u:{subject_id}",
                self.config.store_stickiness_for_s
            )

    @override
    async def load_existing_decisions(
        self,
        subject_id: str,
        flag_keys: list[str],
        experiment_ids: set[str]
    ) -> dict[str, Decision | None]:
        raw_decisions = await self.client.hmget(  # type: ignore[misc]
            f"u:{subject_id}", flag_keys
        )
        decisions: dict[str, Decision | None] = {}
        for key, raw_decision in zip(flag_keys, raw_decisions):
            if not raw_decision:
                decisions[key] = None
            else:
                decision = _load_decision(raw_decision)
                if decision.experiment_id in experiment_ids:
                    decisions[key] = decision
        return decisions


def _load_decision(decision_str: str) -> Decision:
    decision_id, flag_key, experiment_id, value = decision_str.split(
        ";", maxsplit=3
    )
    return Decision(
        DecisionId(decision_id),
        flag_key,
        value,
        experiment_id,
    )


def _dump_decision(decision: Decision) -> str:
    return (f"{decision.id};{decision.flag_key};"
            f"{decision.experiment_id};{decision.value}")
