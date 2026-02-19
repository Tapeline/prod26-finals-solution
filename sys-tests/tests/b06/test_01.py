import httpx
from datetime import datetime, timedelta, timezone

from tests.config import app_url
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    create_event_type,
    create_event_data,
    DEFAULT_EXPERIMENTER_LOGIN
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_b6_reports_basic_flow(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    # create experiment with simple exposure/conversion events
    flag_key = "flag_b6_report"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(
        flag_key=flag_key,
        metrics={"primary": "conversion", "secondary": ["clicks", "exposures"], "guarding": []}
    )

    create_event_type(
        id="exposure_b6",
        name="Exposure",
        schema={"type": "object", "properties": {}},
    )
    create_event_type(
        id="click_b6",
        name="Click",
        schema={
            "type": "object",
            "properties": {"value": {"type": "number"}},
        },
        requires_attribution="exposure_b6",
    )

    # get decision and send paired exposure+conversion in a short window
    decisions = get_flags("user_b6", [flag_key])
    decision_id = decisions[flag_key]["id"]

    now = _now()
    start_at = (now - timedelta(minutes=5)).isoformat()
    end_at = (now + timedelta(minutes=5)).isoformat()

    conv_event = create_event_data(
        event_type="click_b6",
        decision_id=decision_id,
        event_id="evt_conv_b6",
        payload={"value": 1},
    )
    exp_event = create_event_data(
        event_type="exposure_b6",
        decision_id=decision_id,
        event_id="evt_exp_b6",
    )
    decisions2 = get_flags("user_b6_2", [flag_key])
    decision2_id = decisions2[flag_key]["id"]
    exp_2_event = create_event_data(
        event_type="exposure_b6",
        decision_id=decision2_id,
        event_id="evt_exp_b6_2",
    )

    httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [conv_event, exp_event, exp_2_event]},
        timeout=10.0,
    )

    # create a metric in catalog using metric-dsl.
    # Use the same key as experiment.metrics.primary ("clicks") so that
    # report metrics are taken from experiment configuration, not report.
    metric_resp = httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "clicks",
            "expr": "count attributed click_b6"
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert metric_resp.status_code == 201
    metric_resp = httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "exposures",
            "expr": "count exposure_b6"
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert metric_resp.status_code == 201
    metric_resp = httpx.post(
        f"{app_url}/api/v1/metrics/create",
        json={
            "key": "conversion",
            "expr": "count attributed click_b6 / count exposure_b6",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert metric_resp.status_code == 201

    # create a report for the experiment window
    # experiment id is embedded into decision id as prefix
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
    )
    assert report_resp.status_code == 201
    report = report_resp.json()

    # B6-1 period filter: report respects provided window (at least returns some value)
    assert report["start_at"].startswith(start_at[:19])
    assert report["end_at"].startswith(end_at[:19])

    assert report["metrics"]

