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
    get_experiment,
)


def test_b5_4_executes_action_after_guardrail_fires(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-4: Система должна выполнять выбранное действие после срабатывания guardrail."""
    flag_key = "flag_b5_4"
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
        id="error_event_b5_4",
        name="Error Event",
        schema={"type": "object", "properties": {}}
    )
    create_event_type(
        id="total_event_b5_4",
        name="Total Event",
        schema={"type": "object", "properties": {}}
    )

    # Create metric
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "error_rate",
            "expr": "count error_event_b5_4 / count total_event_b5_4",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    # Create guardrail with pause action
    rule_resp = httpx.post(
        f"{app_url}/api/v1/guardrails/for-experiment/{experiment['id']}/create",
        json={
            "experiment_id": experiment["id"],
            "metric_key": "error_rate",
            "threshold": 0.1,  # 10% threshold
            "watch_window_s": 60,  # 1 minute window
            "action": "pause",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()
    rule = rule_resp.json()
    rule_id = rule["id"]

    # Verify experiment is started initially
    exp_resp = get_experiment(experiment["id"])
    assert exp_resp["state"] == "started"

    # Get decision
    decisions = get_flags("user_b5_4", [flag_key])
    decision_id = decisions[flag_key]["id"]

    # Send events that exceed threshold: 20 errors out of 100 total = 20% > 10%
    for i in range(100):
        event = create_event_data(
            event_type="total_event_b5_4",
            decision_id=decision_id,
            event_id=f"evt_total_{i}"
        )
        httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": [event]},
            timeout=10.0,
        ).raise_for_status()

    for i in range(20):  # 20 errors = 20% error rate
        event = create_event_data(
            event_type="error_event_b5_4",
            decision_id=decision_id,
            event_id=f"evt_error_{i}"
        )
        httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": [event]},
            timeout=10.0,
        ).raise_for_status()

    # Wait for guardrail worker to process and execute action
    time.sleep(10)

    # Verify experiment was paused by guardrail action
    exp_resp = get_experiment(experiment["id"])
    assert exp_resp["state"] == "paused", f"Experiment should be paused after guardrail fires, but state is {exp_resp['state']}"
