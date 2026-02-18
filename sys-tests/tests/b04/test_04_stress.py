import httpx
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    get_flags,
    create_event_type,
    create_event_data,
)


def test_stress_concurrent_events(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_stress"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="stress_event",
        name="Stress Test Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            }
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    num_events = 100
    events = []
    for i in range(num_events):
        events.append(create_event_data(
            event_type="stress_event",
            decision_id=decision_id,
            event_id=f"evt_stress_{i}",
            payload={"value": i}
        ))
    
    def send_batch(batch):
        response = httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": batch},
            timeout=30.0
        )
        return response
    
    batch_size = 10
    batches = [events[i:i+batch_size] for i in range(0, len(events), batch_size)]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_batch, batch) for batch in batches]
        results = [f.result() for f in futures]
    
    for result in results:
        assert result.status_code == 200
    
    total_ok = sum(r.json()["ok_count"] for r in results)
    total_duplicates = sum(r.json()["duplicate_count"] for r in results)
    
    assert total_ok + total_duplicates == num_events


def test_stress_rapid_duplicates(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_stress_dup"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="stress_dup_event",
        name="Stress Duplicate Event",
        schema={
            "type": "object",
            "properties": {}
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    event_data = create_event_data(
        event_type="stress_dup_event",
        decision_id=decision_id,
        event_id="evt_rapid_dup"
    )
    
    num_submissions = 20
    
    def send_event():
        response = httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": [event_data]},
            timeout=10.0
        )
        return response.json()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_event) for _ in range(num_submissions)]
        results = [f.result() for f in futures]
    
    total_ok = sum(r["ok_count"] for r in results)
    total_duplicates = sum(r["duplicate_count"] for r in results)
    
    assert total_ok >= 1
    assert total_ok + total_duplicates == num_submissions


def test_stress_mixed_valid_invalid(
    create_default_experimenter_in_db,
    create_default_admin_in_db
):
    flag_key = "flag_stress_mixed"
    create_flag(key=flag_key, type="string", default="default")
    setup_active_experiment(flag_key=flag_key)
    
    create_event_type(
        id="stress_mixed_event",
        name="Stress Mixed Event",
        schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            },
            "required": ["value"]
        }
    )
    
    decisions = get_flags("user_1", [flag_key])
    decision_id = decisions[flag_key]["id"]
    
    events = []
    for i in range(50):
        if i % 2 == 0:
            events.append(create_event_data(
                event_type="stress_mixed_event",
                decision_id=decision_id,
                event_id=f"evt_valid_{i}",
                payload={"value": i}
            ))
        else:
            events.append(create_event_data(
                event_type="stress_mixed_event",
                decision_id=decision_id,
                event_id=f"evt_invalid_{i}",
                payload={}
            ))
    
    response = httpx.post(
        f"{app_url}/api/v1/events/receive",
        json={"events": events},
        timeout=30.0
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["ok_count"] == 25
    assert len(result["errors"]) == 25
