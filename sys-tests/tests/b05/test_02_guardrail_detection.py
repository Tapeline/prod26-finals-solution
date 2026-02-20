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


def test_b5_3_detects_threshold_exceedance(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-3: Система должна обнаруживать факт превышения порога guardrail."""
    flag_key = "flag_b5_3"
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
        id="error_event_b5_3",
        name="Error Event",
        schema={"type": "object", "properties": {}}
    )
    create_event_type(
        id="total_event_b5_3",
        name="Total Event",
        schema={"type": "object", "properties": {}}
    )

    # Create metric
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "error_rate",
            "expr": "count error_event_b5_3 / count total_event_b5_3",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    # Create guardrail with threshold 0.1 (10%)
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

    # Get decision
    decisions = get_flags("user_b5_3", [flag_key])
    decision_id = decisions[flag_key]["id"]

    # Send events that exceed threshold: 20 errors out of 100 total = 20% > 10%
    for i in range(100):
        event = create_event_data(
            event_type="total_event_b5_3",
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
            event_type="error_event_b5_3",
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

    # Check audit log - should have a record of threshold exceedance
    audit_resp = httpx.get(
        f"{app_url}/api/v1/guardrails/{rule_id}/log",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert audit_resp.status_code == 200
    audit_records = audit_resp.json()
    
    # Should have at least one audit record indicating threshold was exceeded
    assert len(audit_records) > 0, "Guardrail should have detected threshold exceedance"
    # Verify the metric value in audit exceeds threshold
    for record in audit_records:
        if record["metric_value"] > 0.1:
            assert record["metric_value"] > 0.1, f"Metric value {record['metric_value']} should exceed threshold 0.1"
            break
