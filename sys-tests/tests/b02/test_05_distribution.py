import uuid
from collections import Counter

from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
)


def test_b2_5_distribution_weights(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    flag_key = "flag_distribution"
    create_flag(key=flag_key, type="string")
    variants = [
        {"name": "A", "value": "val_A", "audience": 50, "is_control": True},
        {"name": "B", "value": "val_B", "audience": 50, "is_control": False}
    ]
    setup_active_experiment(flag_key=flag_key, variants=variants)

    results = []
    total_users = 200

    for i in range(total_users):
        subj_id = f"user_dist_{i}_{uuid.uuid4()}"
        resp = get_flags(subject_id=subj_id, flag_keys=[flag_key])
        results.append(resp[flag_key]["value"])

    counts = Counter(results)
    count_a = counts["val_A"]
    count_b = counts["val_B"]

    assert count_a + count_b == total_users
    assert 80 <= count_a <= 120, f"Bad A distribution: {count_a}"
    assert 80 <= count_b <= 120, f"Bad B distribution: {count_b}"
