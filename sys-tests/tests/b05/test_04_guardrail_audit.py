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


def test_b5_5_records_guardrail_firing_in_audit(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-5: Система должна фиксировать срабатывание guardrail в аудите."""
    flag_key = "flag_b5_5"
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
        id="error_event_b5_5",
        name="Error Event",
        schema={"type": "object", "properties": {}}
    )
    create_event_type(
        id="total_event_b5_5",
        name="Total Event",
        schema={"type": "object", "properties": {}}
    )

    # Create metric
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "error_rate",
            "expr": "count error_event_b5_5 / count total_event_b5_5",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    metric_key = "error_rate"
    threshold = 0.1
    action = "pause"

    # Create guardrail
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

    # Get decision
    decisions = get_flags("user_b5_5", [flag_key])
    decision_id = decisions[flag_key]["id"]

    # Send events that exceed threshold
    for i in range(100):
        event = create_event_data(
            event_type="total_event_b5_5",
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
            event_type="error_event_b5_5",
            decision_id=decision_id,
            event_id=f"evt_error_{i}"
        )
        httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": [event]},
            timeout=10.0,
        ).raise_for_status()

    # Wait for guardrail worker to process
    time.sleep(10)

    # Check audit log for the rule
    audit_resp = httpx.get(
        f"{app_url}/api/v1/guardrails/{rule_id}/log",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert audit_resp.status_code == 200
    audit_records = audit_resp.json()
    
    assert len(audit_records) > 0, "Audit should contain records of guardrail firing"
    
    # Verify audit record contains required fields
    record = audit_records[0]
    assert "id" in record
    assert "rule_id" in record
    assert record["rule_id"] == rule_id
    assert "fired_at" in record
    assert "experiment_id" in record
    assert record["experiment_id"] == experiment["id"]
    assert "metric_key" in record
    assert record["metric_key"] == metric_key
    assert "metric_value" in record
    assert isinstance(record["metric_value"], (int, float))
    assert "taken_action" in record
    assert record["taken_action"] == action

    # Also check experiment-level audit
    exp_audit_resp = httpx.get(
        f"{app_url}/api/v1/guardrails/for-experiment/{experiment['id']}/log",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert exp_audit_resp.status_code == 200
    exp_audit_records = exp_audit_resp.json()
    assert len(exp_audit_records) > 0, "Experiment audit should contain guardrail records"
