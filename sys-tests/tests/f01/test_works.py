import time
import httpx
from datetime import datetime, timedelta, timezone

from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    create_event_type,
    create_event_data,
)


def test_f1_1_guardrail_fires_notification(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
    mailpit,
):
    flag_key = "flag_f1_1"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(
        flag_key=flag_key,
        metrics={
            "primary": "conversion",
            "secondary": [],
            "guarding": ["error_rate"]
        }
    )

    # Create event types
    create_event_type(
        id="error_event_f1_1",
        name="Error Event",
        schema={"type": "object", "properties": {}}
    )
    create_event_type(
        id="total_event_f1_1",
        name="Total Event",
        schema={"type": "object", "properties": {}}
    )

    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "error_rate",
            "expr": "count error_event_f1_1 / count total_event_f1_1",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    metric_key = "error_rate"
    threshold = 0.1
    action = "pause"

    rule_resp = httpx.post(
        f"{app_url}/api/v1/guardrails/for-experiment/{experiment['id']}/create",
        json={
            "experiment_id": experiment["id"],
            "metric_key": metric_key,
            "threshold": threshold,
            "watch_window_s": 60,
            "action": action,
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()
    rule = rule_resp.json()
    rule_id = rule["id"]

    httpx.post(
        f"{app_url}/api/v1/notification-rules/create",
        json={
            "trigger": f"guardrail:{rule_id}",
            "connection_string": "email://test@example.com",
            "template": "Guardrail fired for metric {{ metric_key }}!",
            "rate_limit_s": 60
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    decisions = get_flags("user_f1_1", [flag_key])
    decision_id = decisions[flag_key]["id"]

    for i in range(100):
        event = create_event_data(
            event_type="total_event_f1_1",
            decision_id=decision_id,
            event_id=f"evt_total_{i}"
        )
        httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": [event]},
            timeout=10.0,
        ).raise_for_status()

    # 20% errors
    for i in range(20):
        event = create_event_data(
            event_type="error_event_f1_1",
            decision_id=decision_id,
            event_id=f"evt_error_{i}"
        )
        httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": [event]},
            timeout=10.0,
        ).raise_for_status()

    time.sleep(10)

    message = mailpit.assert_email_received(
        to_address="test@example.com",
        subject_contains="Alphabet Platform Notification"
    )
    body = mailpit.get_message_body(message["ID"])
    assert body.strip() == "Guardrail fired for metric error_rate!"


def test_f1_2_change_fires_and_groups_notifications(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
    mailpit,
):
    flag_key = "flag_f1_1"
    create_flag(key=flag_key, type="string", default="default")

    httpx.post(
        f"{app_url}/api/v1/notification-rules/create",
        json={
            "trigger": f"experiment_lifecycle:*",
            "connection_string": "email://test@example.com",
            "template": "Now in state {{ state }}!",
            "rate_limit_s": 10
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    experiment = setup_active_experiment(
        flag_key=flag_key,
        metrics={
            "primary": "conversion",
            "secondary": [],
            "guarding": ["error_rate"]
        }
    )
    httpx.post(
        f"{app_url}/api/v1/experiments/{experiment['id']}/manage-running",
        json={
            "new_state": "finished"
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    time.sleep(20)

    message = mailpit.assert_email_received(
        to_address="test@example.com",
        subject_contains="Alphabet Platform Notification"
    )
    body = mailpit.get_message_body(message["ID"])
    assert "Now in state" in body
    # assert it does not spam
    assert mailpit.get_email_count() < 3
