import asyncio
import uuid
import httpx

import pytest

from tests.config import app_url
from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
)


def test_b2_4_determinism_sequential_calls(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    flag_key = "flag_det_seq"
    create_flag(key=flag_key, type="string")
    setup_active_experiment(
        flag_key=flag_key, variants=[
            {
                "name": "A",
                "value": "val_A",
                "audience": 50,
                "is_control": True
            },
            {
                "name": "B",
                "value": "val_B",
                "audience": 50,
                "is_control": False
            }
        ]
    )

    subject_id = str(uuid.uuid4())


    initial_resp = get_flags(subject_id=subject_id, flag_keys=[flag_key])
    initial_val = initial_resp[flag_key]["value"]
    initial_exp_id = initial_resp[flag_key]["experiment_id"]

    for i in range(10):
        resp = get_flags(subject_id=subject_id, flag_keys=[flag_key])
        current_val = resp[flag_key]["value"]
        current_exp_id = resp[flag_key]["experiment_id"]

        assert current_val == initial_val, f"Val changed on {i}"
        assert current_exp_id == initial_exp_id, f"EID changed on {i}"


@pytest.mark.asyncio
async def test_b2_4_determinism_concurrent_calls(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    flag_key = "flag_det_concurrent"
    create_flag(key=flag_key, type="string")
    setup_active_experiment(
        flag_key=flag_key, variants=[
            {
                "name": "A",
                "value": "val_A",
                "audience": 50,
                "is_control": True
            },
            {
                "name": "B",
                "value": "val_B",
                "audience": 50,
                "is_control": False
            }
        ]
    )

    subject_id = str(uuid.uuid4())

    async def fetch_flag():
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{app_url}/api/v1/decisions/get-flags",
                json={
                    "subject_id": subject_id,
                    "flags": [flag_key],
                    "attributes": {}
                }
            )
            return resp.raise_for_status().json()["flags"][flag_key]["value"]

    results = await asyncio.gather(*(fetch_flag() for _ in range(10)))

    assert len(set(results)) == 1


def test_b2_4_result_sensitive_to_subject_id(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    flag_key = "flag_det_sensitivity"
    create_flag(key=flag_key, type="string")
    setup_active_experiment(
        flag_key=flag_key, variants=[
            {"name": "A", "value": "A", "audience": 50, "is_control": True},
            {"name": "B", "value": "B", "audience": 50, "is_control": False}
        ]
    )

    found_a = False
    found_b = False

    # Try to get some variants. 50 should be sufficient for all.
    for i in range(50):
        subj_id = f"user_{i}"
        resp = get_flags(subject_id=subj_id, flag_keys=[flag_key])

        found_a |= resp[flag_key]["value"] == "A"
        found_b |= resp[flag_key]["value"] == "B"

        if found_a and found_b:
            break

    assert found_a and found_b
