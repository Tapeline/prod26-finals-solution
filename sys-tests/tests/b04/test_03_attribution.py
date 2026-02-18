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


# TODO: extend the tests when metrics are implemented

def test_b4_4_saves_exposure_with_decision_id(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_4"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="exposure",
        name="Exposure Event",
        schema={
            "type": "object",
            "properties": {}
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    event_data = create_event_data(
        event_type="exposure",
        decision_id=decision_id,
        event_id="evt_exposure_1"
    )
    
    response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [event_data]}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok_count"] == 1


def test_b4_5_attributes_conversion_only_with_exposure(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_5"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="exposure_b4_5",
        name="Exposure Event",
        schema={
            "type": "object",
            "properties": {}
        }
    )
    
    create_event_type(
        id="conversion_b4_5",
        name="Conversion Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            }
        },
        requires_attribution="exposure_b4_5"
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    conversion_data = create_event_data(
        event_type="conversion_b4_5",
        decision_id=decision_id,
        event_id="evt_conv_1",
        payload={"value": 100}
    )
    
    conversion_response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [conversion_data]}
    )
    
    assert conversion_response.status_code == 200
    conv_result = conversion_response.json()
    assert conv_result["ok_count"] == 1
    
    exposure_data = create_event_data(
        event_type="exposure_b4_5",
        decision_id=decision_id,
        event_id="evt_exp_1",
        issued_at=(datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    )
    
    exposure_response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [exposure_data]}
    )
    
    assert exposure_response.status_code == 200
    exp_result = exposure_response.json()
    assert exp_result["ok_count"] == 1
