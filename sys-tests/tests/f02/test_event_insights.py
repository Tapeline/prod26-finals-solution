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
    send_event_data
)


def test_event_insights_no_filters(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_test"
    create_flag(key=flag_key, type="string", default="default")
    exp = setup_active_experiment(flag_key=flag_key)
    create_event_type(
        id="test",
        name="Test Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            },
            "required": ["value"]
        }
    )
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    send_event_data(
        event_type="test",
        decision_id=decision_id,
        event_id="evt_ok_1",
        payload={"value": 42}
    )
    for _ in range(4):
        # one ok, three duplicates
        send_event_data(
            event_type="test",
            decision_id=decision_id,
            event_id="evt_dedup_1",
            payload={"value": 42}
        )
    send_event_data(
        event_type="unknown_event",
        decision_id=decision_id,
        event_id="bad_evt_1",
        payload={}
    )
    send_event_data(
        event_type="test",
        decision_id=decision_id,
        event_id="bad_evt_2",
        payload={"bad_schema": "lalala"}
    )

    time.sleep(8)

    response = httpx.get(
        f"{app_url}/api/v1/insights/{exp['id']}",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )

    assert response.status_code == 200
    insights = response.json()
    assert insights["event_statuses"] == {
        "accepted": 2,
        "duplicate": 3,
        "discarded": 2,
    }
    assert insights["event_types"] == {
        "test": 6,
        "unknown_event": 1,
    }
    assert insights["rejection_reasons"] == {
        "no_such_type": 1,
        "bad_payload": 1
    }
    assert insights["delivery_latency_p95_ms"] > 0
    assert insights["delivery_latency_p75_ms"] > 0
    assert insights["delivery_latency_p50_ms"] > 0


def test_event_insights_filtered(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_test"
    create_flag(key=flag_key, type="string", default="default")
    exp = setup_active_experiment(flag_key=flag_key)
    create_event_type(
        id="test",
        name="Test Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "country": {"type": "string"},
            },
            "required": ["value", "country"]
        }
    )
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]

    for i in range(4):
        send_event_data(
            event_type="test",
            decision_id=decision_id,
            event_id=f"evt_ok_{i}",
            payload={"value": 10, "country": "US" if i % 2 == 0 else "RU"}
        )
    send_event_data(
        event_type="test",
        decision_id=decision_id,
        event_id=f"evt_bad_ru",
        payload={"country": "RU"}
    )
    send_event_data(
        event_type="test",
        decision_id=decision_id,
        event_id=f"evt_bad_us",
        payload={"country": "US"}
    )

    time.sleep(8)

    response = httpx.get(
        f"{app_url}/api/v1/insights/{exp['id']}?country=RU",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )

    assert response.status_code == 200
    insights = response.json()
    assert insights["event_statuses"] == {
        "accepted": 2,
        "discarded": 1,
    }
    assert insights["event_types"] == {
        "test": 3
    }
    assert insights["rejection_reasons"] == {
        "bad_payload": 1
    }
    assert insights["delivery_latency_p95_ms"] > 0
    assert insights["delivery_latency_p75_ms"] > 0
    assert insights["delivery_latency_p50_ms"] > 0
