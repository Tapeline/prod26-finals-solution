import time
import httpx
import pytest
from datetime import datetime, timedelta, timezone

from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    decision_variant_name,
    create_event_type,
    create_event_data,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_b6_3_shows_selected_metrics_in_report(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B6-3: Система должна показывать выбранные метрики эксперимента."""
    flag_key = "flag_b6_3"
    create_flag(key=flag_key, type="string", default="default")
    
    # Create experiment with specific metrics
    primary_metric = "conversion_rate"
    secondary_metrics = ["click_count", "exposure_count"]
    
    experiment = setup_active_experiment(
        flag_key=flag_key,
        metrics={
            "primary": primary_metric,
            "secondary": secondary_metrics,
            "guarding": []
        }
    )

    create_event_type(
        id="exposure_b6_3",
        name="Exposure",
        schema={"type": "object", "properties": {}},
    )
    create_event_type(
        id="click_b6_3",
        name="Click",
        schema={
            "type": "object",
            "properties": {"value": {"type": "number"}},
        },
        requires_attribution="exposure_b6_3",
    )

    # Create all metrics referenced in experiment
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": primary_metric,
            "expr": "count attributed click_b6_3 / count exposure_b6_3",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()
    
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": secondary_metrics[0],
            "expr": "count attributed click_b6_3",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()
    
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": secondary_metrics[1],
            "expr": "count exposure_b6_3",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    # Get decision and send events
    decisions = get_flags("user_b6_3", [flag_key])
    decision_id = decisions[flag_key]["id"]
    variant_name = decision_variant_name(decision_id)

    now = _now()
    start_at = (now - timedelta(minutes=5)).isoformat()
    end_at = (now + timedelta(minutes=5)).isoformat()

    exp_event = create_event_data(
        event_type="exposure_b6_3",
        decision_id=decision_id,
        event_id="evt_exp_b6_3"
    )
    click_event = create_event_data(
        event_type="click_b6_3",
        decision_id=decision_id,
        event_id="evt_click_b6_3",
        payload={"value": 1}
    )

    httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [exp_event, click_event]},
        timeout=10.0,
    ).raise_for_status()

    time.sleep(5 + 1)  # wait for attribution worker

    # Create report
    experiment_id = decision_id.split(":", maxsplit=1)[0]
    report_resp = httpx.post(
        f"{app_url}/api/v1/reports/create",
        json={
            "experiment_id": experiment_id,
            "start_at": start_at,
            "end_at": end_at,
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()
    assert report_resp.status_code == 201
    report = report_resp.json()

    metrics = {m["key"]: m for m in report["metrics"]}

    assert primary_metric in metrics, metrics.keys()
    assert secondary_metrics[0] in metrics, metrics.keys()
    assert secondary_metrics[1] in metrics, metrics.keys()

    # Exact overall values (we sent 1 exposure + 1 attributed click)
    assert metrics[primary_metric]["overall"] == pytest.approx(1.0), metrics
    assert metrics[secondary_metrics[0]]["overall"] == pytest.approx(1.0), metrics
    assert metrics[secondary_metrics[1]]["overall"] == pytest.approx(1.0), metrics

    # Exact per-variant values: for chosen variant we have events; other variant has none.
    other_variants = set(metrics[primary_metric]["per_variant"].keys()) - {variant_name}
    assert len(other_variants) == 1, metrics[primary_metric]["per_variant"]
    other_variant = next(iter(other_variants))

    assert metrics[primary_metric]["per_variant"][variant_name] == pytest.approx(1.0)
    assert metrics[primary_metric]["per_variant"][other_variant] is None

    assert metrics[secondary_metrics[0]]["per_variant"][variant_name] == pytest.approx(1.0)
    assert metrics[secondary_metrics[0]]["per_variant"][other_variant] == pytest.approx(0.0)

    assert metrics[secondary_metrics[1]]["per_variant"][variant_name] == pytest.approx(1.0)
    assert metrics[secondary_metrics[1]]["per_variant"][other_variant] == pytest.approx(0.0)
