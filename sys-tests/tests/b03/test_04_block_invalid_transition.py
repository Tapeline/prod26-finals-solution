import httpx

from tests.helpers import (
    create_flag, create_experiment, setup_active_experiment, send_to_review,
    approve_experiment,
)
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN, DEFAULT_ADMIN_LOGIN


# TODO: others should be tested in unit tests

def test_block_draft_to_start(
    create_default_experimenter_in_db
):
    create_flag()
    exp = create_experiment()

    resp_start = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/start",
        headers=DEFAULT_EXPERIMENTER_LOGIN
    )
    assert resp_start.status_code == 409


def test_block_draft_to_approved(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    create_flag()
    exp = create_experiment()

    resp_approve = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/approve",
        headers=DEFAULT_ADMIN_LOGIN
    )
    assert resp_approve.status_code == 409


def test_cannot_run_experiments_for_one_flag(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    create_flag(key="clash")
    exp1 = setup_active_experiment(flag_key="clash")
    exp2 = create_experiment(flag_key="clash")
    send_to_review(exp2["id"])
    approve_experiment(exp2["id"])

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp2['id']}/start",
        headers=DEFAULT_EXPERIMENTER_LOGIN
    )
    assert response.status_code == 409


def test_cannot_run_experiments_for_one_flag_after_paused(
    create_default_admin_in_db,
    create_default_experimenter_in_db
):
    create_flag(key="clash")
    exp1 = setup_active_experiment(flag_key="clash")
    httpx.post(
        f"{app_url}/api/v1/experiments/{exp1['id']}/manage-running",
        json={
            "new_state": "finished"
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN
    ).raise_for_status()
    exp2 = setup_active_experiment(flag_key="clash")

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp1['id']}/manage-running",
        json={
            "new_state": "started",
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN
    )
    assert response.status_code == 409
