import uuid
from collections import Counter

from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
)


def test_b2_5_distribution_weights(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
    record_property
):
    flag_key = "flag_distribution"
    create_flag(key=flag_key, type="string")
    variants = [
        {"name": "A", "value": "val_A", "audience": 50, "is_control": True},
        {"name": "B", "value": "val_B", "audience": 50, "is_control": False}
    ]
    setup_active_experiment(flag_key=flag_key, variants=variants)

    results = []
    total_users = 1000

    for i in range(total_users):
        subj_id = f"user_dist_{i}_{uuid.uuid4()}"
        resp = get_flags(subject_id=subj_id, flag_keys=[flag_key])
        results.append(resp[flag_key]["value"])

    counts = Counter(results)
    count_a = counts["val_A"]
    count_b = counts["val_B"]
    a_percent = count_a / total_users * 100
    b_percent = count_b / total_users * 100

    record_property("total_users", total_users)
    record_property("variant_A_count", count_a)
    record_property("variant_B_count", count_b)
    record_property(
        "variant_A_percent",
        f"{a_percent:.2f}%"
    )
    record_property(
        "variant_B_percent",
        f"{b_percent:.2f}%"
    )

    assert count_a + count_b == total_users
    assert 45 <= a_percent <= 55, f"Bad A distribution: {a_percent}%"
    assert 45 <= b_percent <= 55, f"Bad B distribution: {b_percent}%"
