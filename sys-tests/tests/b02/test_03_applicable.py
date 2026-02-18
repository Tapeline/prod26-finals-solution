import uuid
from collections import Counter

from tests.config import app_url
from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
)

import httpx


def test_b2_3_returns_variant_if_experiment_applicable(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    flag_key = "flag_active"
    create_flag(type="string", key=flag_key)
    exp = setup_active_experiment(
        flag_key=flag_key,
        variants=[
            {
                "name": "treatment",
                "value": "super_feature",
                "audience": 100,
                "is_control": True
            }
        ]
    )

    response = httpx.post(
        f"{app_url}/api/v1/decisions/get-flags",
        json={
            "subject_id": "user_1",
            "flags": [flag_key],
            "attributes": {}
        }
    )

    assert response.status_code == 200
    decisions = response.json()["flags"]
    assert decisions[flag_key]["value"] == "super_feature"
    assert decisions[flag_key]["experiment_id"] == exp["id"]
    assert decisions[flag_key]["id"] is not None
