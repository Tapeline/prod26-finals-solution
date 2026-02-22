from collections import defaultdict
from datetime import datetime
from typing import Collection

import pytest

from alphabet.decisions.application import (
    MakeDecision,
    DecisionDataStore,
    ExperimentStorage,
    FlagStorage,
    ResolutionRepository, AssignmentStore,
)
from alphabet.decisions.domain import (
    CachedExperiment,
    Decision,
    DecisionId,
    ConflictResolution,
)
from alphabet.experiments.domain.experiment import (
    ExperimentId,
    ConflictPolicy,
    ConflictDomain,
)
from alphabet.shared.infrastructure.time import DefaultTimeProvider
from tests.unit.decisions.helper import variant


class FakeFlagStorage(FlagStorage):
    def __init__(self, defaults: dict[str, str] | None = None):
        self._defaults = defaults or {}
        self._is_ready = True

    def get_default(self, flag_key: str) -> str | None:
        return self._defaults.get(flag_key)

    def set_flag_default(self, flag_key: str, value: str) -> None:
        self._defaults[flag_key] = value

    def is_ready(self) -> bool:
        return self._is_ready

    def mark_ready(self) -> None:
        self._is_ready = True


class FakeExperimentStorage(ExperimentStorage):
    def __init__(self, experiments: dict[str, CachedExperiment] | None = None):
        self._experiments = experiments or {}
        self._is_ready = True

    def get_experiments(
        self, flag_keys: list[str]
    ) -> list[CachedExperiment | None]:
        return [self._experiments.get(k) for k in flag_keys]

    def set_on_flag(
        self, flag_key: str, experiment: CachedExperiment | None
    ) -> None:
        if experiment is None:
            self._experiments.pop(flag_key, None)
        else:
            self._experiments[flag_key] = experiment

    def is_ready(self) -> bool:
        return self._is_ready

    def mark_ready(self) -> None:
        self._is_ready = True


class FakeDecisionDataStore(DecisionDataStore):
    def __init__(self, cooldown_subjects: set[str] | None = None):
        self.cooldown_subjects = cooldown_subjects or set()
        self.decisions: dict[str, dict[str, Decision]] = defaultdict(dict)
        self.assignment_counts: dict[str, int] = defaultdict(int)

    async def is_in_cooldown(self, subject_id: str) -> bool:
        return subject_id in self.cooldown_subjects

    async def save_decisions(
        self, subject_id: str, decisions: Collection[Decision]
    ) -> None:
        for d in decisions:
            self.decisions[subject_id][d.flag_key] = d

    async def load_existing_decisions(
        self, subject_id: str, flag_keys: list[str], experiment_ids: set[str]
    ) -> dict[str, Decision]:
        subject_decisions = self.decisions.get(subject_id, {})
        found = {}
        for key, decision in subject_decisions.items():
            if key in flag_keys or decision.experiment_id in experiment_ids:
                found[key] = decision
        return found

    async def record_experiment_assignments(
        self, subject_id: str, count: int
    ) -> None:
        self.assignment_counts[subject_id] += count

    def seed_decision(self, subject_id: str, decision: Decision):
        self.decisions[subject_id][decision.flag_key] = decision


class FakeResolutionsRepo(ResolutionRepository):
    async def save_resolutions(
        self, resolutions: list[ConflictResolution]
    ) -> None:
        pass

    async def count_conflicts_by_domain(
        self, domain: ConflictDomain
    ) -> dict[ExperimentId, int]:
        return {}

    async def count_conflicts_by_experiment(
        self, experiment_id: ExperimentId
    ) -> tuple[dict[ConflictPolicy, int], dict[ConflictPolicy, int]]:
        return {}, {}

    async def periodic_flush_routine(self) -> None:
        pass


class FakeAssignmentStore(AssignmentStore):
    async def get_variant_distribution(
        self, experiment_id: str
    ) -> dict[str, int]:
        return {}

    async def periodic_flush_routine(self) -> None:
        pass

    async def save_assignments(
        self, decisions: list[Decision], decided_at: datetime, subject_id: str
    ) -> None:
        pass


def _cached_exp(
    exp_id: str,
    flag_key: str,
    is_security_halted: bool = False,
) -> CachedExperiment:
    variants = [
        variant("control", "A", is_control=True),
        variant("treatment", "B"),
    ]
    return CachedExperiment(
        id=exp_id,
        variants=variants,
        targeting=None,
        conflict_domain=None,
        conflict_policy=None,
        priority=1,
        active_flag_key=flag_key,
        experiment_audience=100,
        is_security_halted=is_security_halted,
    )


@pytest.mark.asyncio
async def test_in_cooldown_returns_defaults_for_unassigned():
    store = FakeDecisionDataStore(cooldown_subjects={"user1"})
    flags = FakeFlagStorage(defaults={"f1": "def1", "f2": "def2"})
    exps = FakeExperimentStorage(
        {
            "f1": _cached_exp("e1", "f1"),
            "f2": _cached_exp("e2", "f2"),
        }
    )
    make = MakeDecision(
        store, flags, exps, FakeResolutionsRepo(), FakeAssignmentStore(),
        DefaultTimeProvider()
    )

    result = await make("user1", {}, ["f1", "f2"])

    assert result["f1"].value == "def1"
    assert result["f2"].value == "def2"
    assert "user1" not in store.decisions
    assert store.assignment_counts["user1"] == 0


@pytest.mark.asyncio
async def test_existing_decisions_honored_when_in_cooldown():
    store = FakeDecisionDataStore(cooldown_subjects={"user1"})
    store.seed_decision(
        "user1",
        Decision(
            id=DecisionId("e1:f1:user1:control"),
            flag_key="f1",
            value="A",
            experiment_id="e1",
            variant_id="control",
        ),
    )
    flags = FakeFlagStorage(defaults={"f1": "def1", "f2": "def2"})
    exps = FakeExperimentStorage(
        {
            "f1": _cached_exp("e1", "f1"),
            "f2": _cached_exp("e2", "f2"),
        }
    )
    make = MakeDecision(
        store, flags, exps, FakeResolutionsRepo(), FakeAssignmentStore(),
        DefaultTimeProvider()
    )

    result = await make("user1", {}, ["f1", "f2"])

    assert result["f1"].value == "A"
    assert result["f1"].experiment_id == "e1"
    assert result["f2"].value == "def2"
    assert result["f2"].experiment_id is None


@pytest.mark.asyncio
async def test_security_halted_returns_control():
    store = FakeDecisionDataStore()  # Not in cooldown
    flags = FakeFlagStorage(defaults={"f1": "def1"})

    exps = FakeExperimentStorage(
        {
            "f1": _cached_exp("e1", "f1", is_security_halted=True),
        }
    )
    make = MakeDecision(
        store, flags, exps, FakeResolutionsRepo(), FakeAssignmentStore(),
        DefaultTimeProvider()
    )

    result = await make("user1", {}, ["f1"])

    assert result["f1"].value == "A"  # Control value
    assert result["f1"].experiment_id == "e1"

    saved_decision = store.decisions["user1"]["f1"]
    assert saved_decision.value == "A"
    assert store.assignment_counts["user1"] == 1
