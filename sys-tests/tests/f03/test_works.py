import time
from operator import itemgetter

from tests.helpers import (
    create_flag,
    create_experiment,
    get_flags,
    send_to_review,
    approve_experiment,
    start_experiment,
    DEFAULT_EXPERIMENTER_LOGIN,
)
import httpx
from tests.config import app_url


def given_two_experiments_in_a_domain(domain):
    flag_key_1 = "flag_prio_1"
    flag_key_2 = "flag_prio_2"

    create_flag(key=flag_key_1, type="string", default="def1")
    create_flag(key=flag_key_2, type="string", default="def2")

    exp1 = create_experiment(
        flag_key=flag_key_1,
        conflict_domain=domain,
        conflict_policy="higher_priority",
        priority=10,
    )
    send_to_review(exp1["id"])
    approve_experiment(exp1["id"])
    start_experiment(exp1["id"])

    exp2 = create_experiment(
        flag_key=flag_key_2,
        conflict_domain=domain,
        conflict_policy="higher_priority",
        priority=5,
    )
    send_to_review(exp2["id"])
    approve_experiment(exp2["id"])
    start_experiment(exp2["id"])

    return exp1, exp2


def when_conflict_occurs(exp1, exp2):
    get_flags("user_prio", [exp1["flag_key"], exp2["flag_key"]])


def test_f3_1_conflicts_recorded_per_domain(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    exp1, exp2 = given_two_experiments_in_a_domain("test_domain")
    when_conflict_occurs(exp1, exp2)
    time.sleep(8)
    response = httpx.get(
        f"{app_url}/api/v1/decisions/conflicts/by-domain/test_domain",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "per_experiment": {
            exp1["id"]: 1,
            exp2["id"]: 1,
        }
    }


def test_f3_2_conflicts_recorded_per_experiment(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    exp1, exp2 = given_two_experiments_in_a_domain("test_domain")
    when_conflict_occurs(exp1, exp2)
    winner, loser = sorted((exp1, exp2), key=itemgetter("priority"))
    time.sleep(8)
    winner_response = httpx.get(
        f"{app_url}/api/v1/decisions/conflicts/by-experiment/{winner['id']}",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    loser_response = httpx.get(
        f"{app_url}/api/v1/decisions/conflicts/by-experiment/{loser['id']}",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert winner_response.status_code == 200
    assert loser_response.status_code == 200
    assert winner_response.json() == {
        "wins": {"higher_priority": 1},
        "losses": {}
    }
    assert loser_response.json() == {
        "wins": {},
        "losses": {"higher_priority": 1}
    }
