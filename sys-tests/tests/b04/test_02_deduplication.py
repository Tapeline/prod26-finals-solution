import httpx
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    create_event_type,
    create_event_data,
)


def test_b4_3_deduplicates_duplicate_events(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_b4_3"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="test_event_dedup",
        name="Test Event Dedup",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            }
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    event_data = create_event_data(
        event_type="test_event_dedup",
        decision_id=decision_id,
        event_id="evt_dedup_1",
        payload={"value": 42}
    )
    
    response1 = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [event_data]}
    )
    assert response1.status_code == 200
    result1 = response1.json()
    assert result1["ok_count"] == 1
    assert result1["duplicate_count"] == 0
    
    response2 = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": [event_data]}
    )
    assert response2.status_code == 200
    result2 = response2.json()
    assert result2["ok_count"] == 0
    assert result2["duplicate_count"] == 1
