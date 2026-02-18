import httpx
from datetime import datetime, timezone
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    create_event_type,
    create_event_data,
)


def test_b4_1_accepts_valid_event(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_1_good"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="test_event_good",
        name="Test Event",
        schema={
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "category": {"type": "string"}
            },
            "required": ["amount", "category"]
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    event_data = create_event_data(
        event_type="test_event_good",
        decision_id=decision_id,
        event_id="evt_good_1",
        payload={"amount": 100, "category": "test"}
    )
    
    response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [event_data]}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok_count"] == 1
    assert result["duplicate_count"] == 0
    assert len(result["errors"]) == 0


def test_b4_1_validates_field_types(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_1"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="test_event",
        name="Test Event",
        schema={
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "category": {"type": "string"}
            },
            "required": ["amount", "category"]
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    event_data = create_event_data(
        event_type="test_event",
        decision_id=decision_id,
        event_id="evt_1",
        payload={"amount": "not_a_number", "category": "test"}
    )
    
    response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [event_data]}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok_count"] == 0
    assert len(result["errors"]) > 0
    assert result["errors"]["0"] == "bad_payload"


def test_b4_2_validates_required_fields(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_2"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="test_event_req",
        name="Test Event Required",
        schema={
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "category": {"type": "string"}
            },
            "required": ["amount", "category"]
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    event_data = create_event_data(
        event_type="test_event_req",
        decision_id=decision_id,
        event_id="evt_2",
        payload={"amount": 100}
    )
    
    response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [event_data]}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok_count"] == 0
    assert len(result["errors"]) > 0
    assert result["errors"]["0"] == "bad_payload"
