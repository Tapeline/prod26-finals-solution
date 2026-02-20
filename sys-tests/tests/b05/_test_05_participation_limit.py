"""B5-6: Participation limit — count-based cooldown (ADR002).

Cooldown is triggered after `cooldown_experiment_threshold` new experiment
assignments (config: 1). It lasts `cooldown_for_s` (config: 15s).
"""

import time

from tests.config import app_url
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flag_decision,
)


def test_b5_6_immediate_block_after_first_assignment(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-6: First assignment triggers cooldown; second experiment gets default immediately."""
    flag_key_1 = "flag_b5_6_immediate_1"
    flag_key_2 = "flag_b5_6_immediate_2"

    subject_id = "user_b5_6_immediate"
    create_flag(key=flag_key_1, type="string", default="default")
    create_flag(key=flag_key_2, type="string", default="default")
    setup_active_experiment(flag_key=flag_key_1)
    setup_active_experiment(flag_key=flag_key_2)

    # First request: participate in exp1 → cooldown triggered (threshold=1)
    d1 = get_flag_decision(subject_id, flag_key_1)
    assert d1["value"] != "default"
    assert d1["experiment_id"] is not None

    # Immediately request flag2: must get default (no sleep)
    d2 = get_flag_decision(subject_id, flag_key_2)
    assert d2["value"] == "default"
    assert d2["experiment_id"] is None


def test_b5_6_after_cooldown_ttl_user_can_participate(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-6: After cooldown TTL expires, user can participate in new experiments."""
    flag_key_1 = "flag_b5_6_ttl_1"
    flag_key_2 = "flag_b5_6_ttl_2"

    subject_id = "user_b5_6_ttl"
    create_flag(key=flag_key_1, type="string", default="default")
    create_flag(key=flag_key_2, type="string", default="default")
    setup_active_experiment(flag_key=flag_key_1)
    setup_active_experiment(flag_key=flag_key_2)

    d1 = get_flag_decision(subject_id, flag_key_1)
    assert d1["value"] != "default"
    assert d1["experiment_id"] is not None

    # Second experiment blocked during cooldown
    d2_blocked = get_flag_decision(subject_id, flag_key_2)
    assert d2_blocked["value"] == "default"
    assert d2_blocked["experiment_id"] is None

    # Wait for cooldown TTL to expire (config: 15s)
    time.sleep(16)

    # Now user can participate in exp2
    d2_after = get_flag_decision(subject_id, flag_key_2)
    assert d2_after["value"] != "default"
    assert d2_after["experiment_id"] is not None


def test_b5_6_sticky_decisions_preserved_during_cooldown(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-6: Already assigned values stay the same during cooldown (stickiness)."""
    flag_key = "flag_b5_6_sticky"
    subject_id = "user_b5_6_sticky"

    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)

    first = get_flag_decision(subject_id, flag_key)
    assert first["experiment_id"] is not None
    assert first["value"] != "default"

    # Immediately request same flag again: same decision (cached), cooldown triggered
    second = get_flag_decision(subject_id, flag_key)
    assert second == first
