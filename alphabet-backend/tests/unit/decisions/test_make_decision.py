"""Unit tests for make_decision (ADR002 deterministic bucketing)."""

import pytest

from alphabet.decisions.domain import make_decision, distribute_variants
from alphabet.experiments.domain.experiment import Percentage, Variant
from tests.unit.decisions.helper import variant


def test_deterministic_same_input_same_output():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(100, variants)
    d1 = make_decision("f", "def", "e1", axis, "user1")
    d2 = make_decision("f", "def", "e1", axis, "user1")
    assert d1.value == d2.value
    assert d1.id == d2.id
    assert d1.experiment_id == d2.experiment_id


def test_different_subjects_may_differ():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(100, variants)
    seen = set()
    for i in range(200):
        d = make_decision("f", "def", "e1", axis, f"user_{i}")
        seen.add(d.value)
    assert "A" in seen
    assert "B" in seen


def test_bucket_none_returns_default():
    axis = [None] * 100
    d = make_decision("f", "fallback", "e1", axis, "user_x")
    assert d.value == "fallback"
    assert d.experiment_id == "e1"
    assert "!default" in str(d.id)


def test_experiment_id_preserved():
    variants = [variant("control", "A", 100, is_control=True)]
    axis = distribute_variants(100, variants)
    d = make_decision("flag1", "def", "exp-123", axis, "u1")
    assert d.experiment_id == "exp-123"
    assert d.flag_key == "flag1"
    assert "exp-123" in str(d.id)
