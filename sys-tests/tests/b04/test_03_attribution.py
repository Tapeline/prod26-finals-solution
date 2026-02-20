import os
import time

import httpx
from datetime import datetime, timezone, timedelta
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    create_event_type,
    create_event_data,
)


def test_b4_4_saves_exposure_with_decision_id(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_4"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(flag_key=flag_key, metrics={
        "primary": "conversion",
        "secondary": [],
        "guarding": []
    })

    create_event_type(
        id="exposure_b4_4",
        name="Exposure Event",
        schema={
            "type": "object",
            "properties": {}
        }
    )

    create_event_type(
        id="click_b4_4",
        name="Click Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            }
        },
        requires_attribution="exposure_b4_4"
    )

    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "conversion",
            "expr": "count attributed click_b4_4",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]

    exposure_event = create_event_data(
        event_type="exposure_b4_4",
        decision_id=decision_id,
        event_id="evt_exposure_1"
    )

    httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [exposure_event]}
    ).raise_for_status()

    click_event = create_event_data(
        event_type="click_b4_4",
        decision_id=decision_id,
        event_id="evt_click_1",
        payload={"value": 100}
    )

    httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [click_event]}
    ).raise_for_status()

    time.sleep(5 + 1)  # wait for the attribution worker

    report_resp = httpx.post(
        f"{app_url}/api/v1/reports/create",
        json={
            "experiment_id": experiment["id"],
            "start_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "end_at": (datetime.now() + timedelta(days=1)).isoformat(),
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status().json()

    assert report_resp["metrics"][0]["overall"] == 1, report_resp


def test_b4_5_attributes_conversion_only_with_exposure(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_5"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(flag_key=flag_key, metrics={
        "primary": "conversion",
        "secondary": [],
        "guarding": []
    })

    create_event_type(
        id="exposure_b4_5",
        name="Exposure Event",
        schema={
            "type": "object",
            "properties": {}
        }
    )

    create_event_type(
        id="click_b4_5",
        name="Click Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            }
        },
        requires_attribution="exposure_b4_5"
    )

    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "conversion",
            "expr": "count attributed click_b4_5",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]

    unattributed_click = create_event_data(
        event_type="click_b4_5",
        decision_id=decision_id,
        event_id="evt_conv_1",
        payload={"value": 100}
    )

    httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [unattributed_click]}
    ).raise_for_status()

    time.sleep(5 + 1)  # wait for the attribution worker

    report_resp = httpx.post(
        f"{app_url}/api/v1/reports/create",
        json={
            "experiment_id": experiment["id"],
            "start_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "end_at": (datetime.now() + timedelta(days=1)).isoformat(),
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status().json()

    assert report_resp["metrics"][0]["overall"] == 0, report_resp
