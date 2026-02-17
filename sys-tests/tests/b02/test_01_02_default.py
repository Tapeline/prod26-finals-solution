from tests.config import app_url
from tests.helpers import create_flag

import httpx

import uuid
from collections import Counter

from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
)


def test_b2_1_returns_default_if_no_active_experiment(
    create_default_experimenter_in_db
):
    flag_key = "flag_no_exp"
    default_val = "false"
    create_flag(key=flag_key, default=default_val)

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
    assert decisions[flag_key]["value"] == default_val
    assert decisions[flag_key]["experiment_id"] is None


def test_b2_2_returns_default_if_targeting_mismatch(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    flag_key = "flag_targeting"
    flag_default = "default_value"
    targeting_rule = 'country == "RU"'
    create_flag(key=flag_key, default=flag_default, type="string")
    setup_active_experiment(
        flag_key=flag_key,
        targeting=targeting_rule,
    )

    response = httpx.post(
        f"{app_url}/api/v1/decisions/get-flags",
        json={
            "subject_id": "user_1",
            "flags": [flag_key],
            "attributes": {"country": "NIBIRU"}
        }
    )
    assert response.status_code == 200
    decisions = response.json()["flags"]
    assert decisions[flag_key]["value"] == flag_default
    assert decisions[flag_key]["experiment_id"] is None
