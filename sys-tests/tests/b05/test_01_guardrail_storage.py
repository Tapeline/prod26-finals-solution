import httpx
from datetime import datetime, timedelta, timezone

from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
)


def test_b5_1_stores_metric_key_for_guardrail(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-1: Система должна хранить `metric_key` для guardrail-правила."""
    flag_key = "flag_b5_1"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(flag_key=flag_key)

    # Create a metric first
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "error_rate",
            "expr": "count error_event / count total_event",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    # Create guardrail rule with metric_key
    rule_resp = httpx.post(
        f"{app_url}/api/v1/guardrails/for-experiment/{experiment['id']}/create",
        json={
            "experiment_id": experiment["id"],
            "metric_key": "error_rate",
            "threshold": 0.1,
            "watch_window_s": 3600,
            "action": "pause",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert rule_resp.status_code == 201
    rule = rule_resp.json()
    assert rule["metric_key"] == "error_rate"


def test_b5_2_stores_threshold_for_guardrail(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B5-2: Система должна хранить порог guardrail-правила."""
    flag_key = "flag_b5_2"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(flag_key=flag_key)

    # Create a metric first
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "error_rate",
            "expr": "count error_event / count total_event",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    threshold = 0.15
    # Create guardrail rule with threshold
    rule_resp = httpx.post(
        f"{app_url}/api/v1/guardrails/for-experiment/{experiment['id']}/create",
        json={
            "experiment_id": experiment["id"],
            "metric_key": "error_rate",
            "threshold": threshold,
            "watch_window_s": 3600,
            "action": "pause",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert rule_resp.status_code == 201
    rule = rule_resp.json()
    assert rule["threshold"] == threshold

    # Verify by reading the rule back
    rule_id = rule["id"]
    read_resp = httpx.get(
        f"{app_url}/api/v1/guardrails/{rule_id}",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert read_resp.status_code == 200
    read_rule = read_resp.json()
    assert read_rule["threshold"] == threshold
