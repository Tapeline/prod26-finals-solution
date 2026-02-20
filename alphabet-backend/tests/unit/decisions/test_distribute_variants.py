"""Unit tests for distribute_variants (ADR002 bucketing)."""

import pytest

from alphabet.decisions.domain import distribute_variants
from alphabet.experiments.domain.experiment import Percentage, Variant
from tests.unit.decisions.helper import variant


def test_audience_zero_returns_all_none():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(0, variants)
    assert axis == [None] * 100


def test_audience_negative_clamped_to_zero():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(-10, variants)
    assert axis == [None] * 100


def test_audience_over_100_clamped():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(150, variants)
    # Clamped to 100, so 50 control + 50 treatment
    assert axis.count(("control", "A")) == 50
    assert axis.count(("treatment", "B")) == 50
    assert axis.count(None) == 0


def test_audience_100_two_equal_variants():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(100, variants)
    assert axis.count(("control", "A")) == 50
    assert axis.count(("treatment", "B")) == 50
    assert axis.count(None) == 0
    assert len(axis) == 100


def test_audience_50_two_equal_variants():
    variants = [
        variant("control", "A", 50, is_control=True),
        variant("treatment", "B", 50),
    ]
    axis = distribute_variants(50, variants)
    assert axis.count(("control", "A")) == 25
    assert axis.count(("treatment", "B")) == 25
    assert axis.count(None) == 50


def test_audience_100_unequal_variants():
    variants = [
        variant("control", "A", 70, is_control=True),
        variant("treatment", "B", 30),
    ]
    axis = distribute_variants(100, variants)
    assert axis.count(("control", "A")) == 70
    assert axis.count(("treatment", "B")) == 30
    assert axis.count(None) == 0


def test_audience_100_three_variants():
    variants = [
        variant("control", "A", 40, is_control=True),
        variant("treatment", "B", 35),
        variant("variantc", "C", 25),
    ]
    axis = distribute_variants(100, variants)
    assert axis.count(("control", "A")) == 40
    assert axis.count(("treatment", "B")) == 35
    assert axis.count(("variantc", "C")) == 25
    assert axis.count(None) == 0


def test_single_variant_gets_all_in_experiment_buckets():
    variants = [variant("control", "A", 100, is_control=True)]
    axis = distribute_variants(60, variants)
    assert axis.count(("control", "A")) == 60
    assert axis.count(None) == 40


def test_small_audience_small_variant_shares():
    variants = [
        variant("control", "A", 10, is_control=True),
        variant("treatment", "B", 90),
    ]
    axis = distribute_variants(10, variants)
    # 10% of 10 = 1 for control, 90% of 10 = 9 for treatment
    assert axis.count(("control", "A")) == 1
    assert axis.count(("treatment", "B")) == 9
    assert axis.count(None) == 90
