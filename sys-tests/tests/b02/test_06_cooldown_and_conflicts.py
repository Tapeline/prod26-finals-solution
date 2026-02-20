"""System tests for cooldown and conflict resolution (ADR002, ADR007)."""

from tests.helpers import (
    create_flag,
    create_experiment,
    get_flags,
    send_to_review,
    approve_experiment,
    start_experiment,
)


def test_b2_6_conflict_one_or_none_both_get_default(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B2-6: ONE_OR_NONE policy — both conflicting experiments return default."""
    flag_key_1 = "flag_conflict_1"
    flag_key_2 = "flag_conflict_2"
    domain = "test_domain"

    create_flag(key=flag_key_1, type="string", default="def1")
    create_flag(key=flag_key_2, type="string", default="def2")

    exp1 = create_experiment(
        flag_key=flag_key_1,
        conflict_domain=domain,
        conflict_policy="one_or_none",
    )
    send_to_review(exp1["id"])
    approve_experiment(exp1["id"])
    start_experiment(exp1["id"])

    exp2 = create_experiment(
        flag_key=flag_key_2,
        conflict_domain=domain,
        conflict_policy="one_or_none",
    )
    send_to_review(exp2["id"])
    approve_experiment(exp2["id"])
    start_experiment(exp2["id"])

    result = get_flags("user_conflict", [flag_key_1, flag_key_2])

    # Both should get default (ONE_OR_NONE drops all in domain)
    assert result[flag_key_1]["value"] == "def1"
    assert result[flag_key_1]["experiment_id"] is None
    assert result[flag_key_2]["value"] == "def2"
    assert result[flag_key_2]["experiment_id"] is None


def test_b2_6_conflict_higher_priority_one_wins(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B2-6: HIGHER_PRIORITY — experiment with lower priority value wins."""
    flag_key_1 = "flag_prio_1"
    flag_key_2 = "flag_prio_2"
    domain = "prio_domain"

    create_flag(key=flag_key_1, type="string", default="def1")
    create_flag(key=flag_key_2, type="string", default="def2")

    exp1 = create_experiment(
        flag_key=flag_key_1,
        conflict_domain=domain,
        conflict_policy="higher_priority",
        priority=10,
    )
    send_to_review(exp1["id"])
    approve_experiment(exp1["id"])
    start_experiment(exp1["id"])

    exp2 = create_experiment(
        flag_key=flag_key_2,
        conflict_domain=domain,
        conflict_policy="higher_priority",
        priority=5,
    )
    send_to_review(exp2["id"])
    approve_experiment(exp2["id"])
    start_experiment(exp2["id"])

    result = get_flags("user_prio", [flag_key_1, flag_key_2])

    # exp2 (priority 5) wins over exp1 (priority 10)
    assert result[flag_key_2]["experiment_id"] is not None
    assert result[flag_key_2]["value"] != "def2"
    assert result[flag_key_1]["value"] == "def1"
    assert result[flag_key_1]["experiment_id"] is None
