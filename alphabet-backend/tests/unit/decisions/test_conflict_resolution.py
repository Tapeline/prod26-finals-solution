"""Unit tests for conflict resolution (ADR007)."""

from alphabet.decisions.application import MakeDecision
from alphabet.decisions.domain import CachedExperiment
from alphabet.experiments.domain.experiment import ConflictPolicy
from tests.unit.decisions.helper import variant


def _cached_exp(
    exp_id: str,
    flag_key: str,
    domain: str | None = None,
    policy: ConflictPolicy | None = None,
    priority: int | None = None,
) -> CachedExperiment:
    variants = [
        variant("control", "A", is_control=True),
        variant("treatment", "B"),
    ]
    return CachedExperiment(
        id=exp_id,
        variants=variants,
        targeting=None,
        conflict_domain=domain,
        conflict_policy=policy,
        priority=priority,
        active_flag_key=flag_key,
        experiment_audience=100,
    )


class TestConflictResolution:
    """ONE_OR_NONE and HIGHER_PRIORITY policies."""

    def test_one_experiment_in_domain_survives(self):
        make = MakeDecision(
            decision_data=None,  # type: ignore
            flags=None,  # type: ignore
            experiments=None,  # type: ignore
            resolutions_repo=None,  # type: ignore
        )
        exps = [
            _cached_exp(
                "e1", "f1", domain="d1", policy=ConflictPolicy.ONE_OR_NONE
            ),
        ]
        survivors, resolutions = make._resolve_conflicts(exps)
        assert len(survivors) == 1
        assert survivors[0].id == "e1"

    def test_one_or_none_drops_all_in_domain(self):
        make = MakeDecision(
            decision_data=None,  # type: ignore
            flags=None,  # type: ignore
            experiments=None,  # type: ignore
            resolutions_repo=None,  # type: ignore
        )
        exps = [
            _cached_exp(
                "e1", "f1", domain="d1", policy=ConflictPolicy.ONE_OR_NONE
            ),
            _cached_exp(
                "e2", "f2", domain="d1", policy=ConflictPolicy.ONE_OR_NONE
            ),
        ]
        survivors, resolutions = make._resolve_conflicts(exps)
        assert len(survivors) == 0
        assert len(resolutions) == 2
        for r in resolutions:
            assert r.experiment_applied is False

    def test_higher_priority_selects_lowest_priority_value(self):
        make = MakeDecision(
            decision_data=None,  # type: ignore
            flags=None,  # type: ignore
            experiments=None,  # type: ignore
            resolutions_repo=None,  # type: ignore
        )
        exps = [
            _cached_exp(
                "e1",
                "f1",
                domain="d1",
                policy=ConflictPolicy.HIGHER_PRIORITY,
                priority=10,
            ),
            _cached_exp(
                "e2",
                "f2",
                domain="d1",
                policy=ConflictPolicy.HIGHER_PRIORITY,
                priority=5,
            ),
        ]
        survivors, resolutions = make._resolve_conflicts(exps)
        assert len(survivors) == 1
        assert survivors[0].priority == 5
        assert survivors[0].id == "e2"

    def test_higher_priority_tie_breaker_deterministic(self):
        make = MakeDecision(
            decision_data=None,  # type: ignore
            flags=None,  # type: ignore
            experiments=None,  # type: ignore
            resolutions_repo=None,  # type: ignore
        )
        exps = [
            _cached_exp(
                "e_a",
                "f1",
                domain="d1",
                policy=ConflictPolicy.HIGHER_PRIORITY,
                priority=1,
            ),
            _cached_exp(
                "e_b",
                "f2",
                domain="d1",
                policy=ConflictPolicy.HIGHER_PRIORITY,
                priority=1,
            ),
        ]
        survivors, _ = make._resolve_conflicts(exps)
        assert len(survivors) == 1
        # Same call must yield same winner
        survivors2, _ = make._resolve_conflicts(exps)
        assert survivors2[0].id == survivors[0].id

    def test_none_domain_experiments_survive(self):
        make = MakeDecision(
            decision_data=None,  # type: ignore
            flags=None,  # type: ignore
            experiments=None,  # type: ignore
            resolutions_repo=None,  # type: ignore
        )
        exps = [
            _cached_exp("e1", "f1", domain=None, policy=None),
            _cached_exp("e2", "f2", domain=None, policy=None),
        ]
        survivors, resolutions = make._resolve_conflicts(exps)
        assert len(survivors) == 2
