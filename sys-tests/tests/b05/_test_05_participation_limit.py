import time

from tests.config import app_url
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flag_decision,
)


def test_b5_6_limits_user_participation_in_new_experiments_after_time(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-6: Система должна ограничивать постоянное участие пользователя в экспериментах."""
    flag_key_1 = "flag_b5_6_1"
    flag_key_2 = "flag_b5_6_2"

    subject_id = "user_b5_6"
    create_flag(key=flag_key_1, type="string", default="default")
    create_flag(key=flag_key_2, type="string", default="default")
    setup_active_experiment(flag_key=flag_key_1)
    setup_active_experiment(flag_key=flag_key_2)

    # Participate in the first experiment
    d1 = get_flag_decision(subject_id, flag_key_1)
    assert d1["value"] != "default"
    assert d1["experiment_id"] is not None

    # Wait long enough for cooldown cycle to kick in (config: 15s)
    time.sleep(20)

    # Try to participate in the second experiment: must be blocked -> default
    d2 = get_flag_decision(subject_id, flag_key_2)
    assert d2["value"] == "default"
    assert d2["experiment_id"] is None


def test_b5_6_sticky_default_when_blocked_from_new_experiment(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-6: После окончания cooldown пользователь может участвовать в новом эксперименте."""
    flag_key_1 = "flag_b5_6_1_sticky"
    flag_key_2 = "flag_b5_6_2_sticky"

    subject_id = "user_b5_6_sticky"
    create_flag(key=flag_key_1, type="string", default="default")
    create_flag(key=flag_key_2, type="string", default="default")
    setup_active_experiment(flag_key=flag_key_1)
    setup_active_experiment(flag_key=flag_key_2)

    d1 = get_flag_decision(subject_id, flag_key_1)
    assert d1["value"] != "default"
    assert d1["experiment_id"] is not None

    time.sleep(20)

    d2_during_cooldown = get_flag_decision(subject_id, flag_key_2)
    assert d2_during_cooldown["value"] == "default"
    assert d2_during_cooldown["experiment_id"] is None

    # Wait for cooldown to end (config: 15s for cooldown, first call started it)
    time.sleep(20)

    d2_after_cooldown = get_flag_decision(subject_id, flag_key_2)
    assert d2_after_cooldown["value"] != "default"
    assert d2_after_cooldown["experiment_id"] is not None


def test_b5_6_assigned_values_stay_same_even_if_user_enters_cooldown(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-6: Уже выданные значения флагов должны оставаться неизменными во время cooldown."""
    flag_key = "flag_b5_6_stable"
    subject_id = "user_b5_6_stable"

    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)

    first = get_flag_decision(subject_id, flag_key)
    assert first["experiment_id"] is not None
    assert first["value"] != "default"

    # Wait long enough so that the next request triggers cooldown.
    time.sleep(20)

    second = get_flag_decision(subject_id, flag_key)
    assert second == first
