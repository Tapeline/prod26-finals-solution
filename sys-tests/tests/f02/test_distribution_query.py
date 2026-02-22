import time
import uuid
from collections import Counter

import httpx

from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
    app_url,
    DEFAULT_EXPERIMENTER_LOGIN,
)


def test_distribution_query(
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
    exp = setup_active_experiment(flag_key=flag_key, variants=variants)

    results = []
    total_users = 100

    for i in range(total_users):
        subj_id = f"user_dist_{i}_{uuid.uuid4()}"
        resp = get_flags(subject_id=subj_id, flag_keys=[flag_key])
        print(resp)
        results.append(resp[flag_key]["value"])

    counts = Counter(results)
    count_a = counts["val_A"]
    count_b = counts["val_B"]

    time.sleep(8)

    response = httpx.get(
        f"{app_url}/api/v1/decisions/distribution/{exp['id']}",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )

    assert response.status_code == 200
    distribution = response.json()
    assert distribution.get("A") == count_a, distribution
    assert distribution.get("B") == count_b, distribution
