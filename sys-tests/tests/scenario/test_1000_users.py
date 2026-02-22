import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import random

import httpx

from tests.helpers import (
    create_flag,
    get_flags,
    setup_active_experiment,
create_event_type,
create_event_data
)
from tests.config import app_url


def test_1000_users(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
    record_property
):
    flag_key = "test_100_users"
    create_flag(key=flag_key, type="string")
    variants = [
        {"name": "A", "value": "val_A", "audience": 50, "is_control": True},
        {"name": "B", "value": "val_B", "audience": 35, "is_control": False},
        {"name": "C", "value": "val_C", "audience": 15, "is_control": False},
    ]
    setup_active_experiment(flag_key=flag_key, variants=variants)

    create_event_type(
        id="exposure",
        name="Exposure",
        schema={},
    )
    create_event_type(
        id="click",
        name="Click",
        schema={},
        requires_attribution="exposure"
    )

    total_users = 1000

    def user_journey(uid):
        decision = get_flags(subject_id=uid, flag_keys=[flag_key])[flag_key]
        time.sleep(random.randint(1, 10) / 10)
        events = [create_event_data(
            event_type="exposure",
            decision_id=decision["id"],
            event_id=str(uuid.uuid4()),
            payload={}
        )]
        if random.choice((True, False)):
            events.append(create_event_data(
                event_type="click",
                decision_id=decision["id"],
                event_id=str(uuid.uuid4()),
                payload={}
            ))
        response = httpx.post(
            f"{app_url}/api/v1/events/receive",
            json={"events": events}
        ).raise_for_status().json()
        return response["ok_count"] == len(events), response, uid

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(user_journey, f"u{i}")
            for i in range(total_users)
        ]
        results = [f.result() for f in futures]

    assert all(
        is_ok for is_ok, *_ in results
    ), [(response, uid) for is_ok, response, uid in results if not is_ok]
