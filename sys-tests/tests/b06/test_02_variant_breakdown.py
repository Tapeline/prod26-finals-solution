import time
import httpx
import pytest
from datetime import datetime, timedelta, timezone

from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    find_subject_for_variant_name,
    create_event_type,
    create_event_data,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_b6_2_shows_report_by_variant(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B6-2: Система должна показывать отчёт в разрезе вариантов."""
    flag_key = "flag_b6_2"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(
        flag_key=flag_key,
        metrics={"primary": "conversion", "secondary": [], "guarding": []}
    )

    create_event_type(
        id="exposure_b6_2",
        name="Exposure",
        schema={"type": "object", "properties": {}},
    )
    create_event_type(
        id="click_b6_2",
        name="Click",
        schema={
            "type": "object",
            "properties": {"value": {"type": "number"}},
        },
        requires_attribution="exposure_b6_2",
    )

    # Create metric
    httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "conversion",
            "expr": "count attributed click_b6_2 / count exposure_b6_2",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()

    # Pick two subjects that land in different variants (control/treatment)
    _, control_decision = find_subject_for_variant_name(
        flag_key,
        "control",
        prefix="user_b6_2",
    )
    _, treatment_decision = find_subject_for_variant_name(
        flag_key,
        "treatment",
        prefix="user_b6_2",
    )
    decision_control_id = control_decision["id"]
    decision_treatment_id = treatment_decision["id"]

    now = _now()
    start_at = (now - timedelta(minutes=5)).isoformat()
    end_at = (now + timedelta(minutes=5)).isoformat()

    # Send exposure and conversion events for variant 1
    exp_1 = create_event_data(
        event_type="exposure_b6_2",
        decision_id=decision_control_id,
        event_id="evt_exp_control",
    )
    click_1 = create_event_data(
        event_type="click_b6_2",
        decision_id=decision_control_id,
        event_id="evt_click_control",
        payload={"value": 1},
    )

    exp_2 = create_event_data(
        event_type="exposure_b6_2",
        decision_id=decision_treatment_id,
        event_id="evt_exp_treatment",
    )
    click_2 = create_event_data(
        event_type="click_b6_2",
        decision_id=decision_treatment_id,
        event_id="evt_click_treatment",
        payload={"value": 1},
    )

    httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [exp_1, click_1, exp_2, click_2]},
        timeout=10.0,
    ).raise_for_status()

    time.sleep(10)  # wait for attribution worker

    # Create report
    report_resp = httpx.post(
        f"{app_url}/api/v1/reports/create",
        json={
            "experiment_id": experiment["id"],
            "start_at": start_at,
            "end_at": end_at,
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    ).raise_for_status()
    assert report_resp.status_code == 201
    report = report_resp.json()

    metrics = {m["key"]: m for m in report["metrics"]}
    assert "conversion" in metrics, report
    metric = metrics["conversion"]

    # Exact values: 2 clicks / 2 exposures = 1.0 overall.
    assert metric["overall"] == pytest.approx(1.0), metric

    # Per-variant exact values: 1 click / 1 exposure = 1.0 for both variants.
    assert metric["per_variant"]["control"] == pytest.approx(1.0), metric
    assert metric["per_variant"]["treatment"] == pytest.approx(1.0), metric
