import httpx

from tests.helpers import (
    create_experiment,
    send_to_review, create_flag, get_experiment, approve_experiment,
)
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN


def test_block_start_without_approvals(
    create_default_experimenter_in_db
):
    create_flag()
    exp = create_experiment()
    send_to_review(exp["id"])

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/start",
        headers=DEFAULT_EXPERIMENTER_LOGIN
    )

    assert response.status_code == 409
    assert get_experiment(exp["id"])["state"] == "in_review"


def test_can_start_after_accepted(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
):
    create_flag()
    exp = create_experiment()
    send_to_review(exp["id"])
    approve_experiment(exp["id"])

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/start",
        headers=DEFAULT_EXPERIMENTER_LOGIN
    )

    assert response.status_code == 200
    assert get_experiment(exp["id"])["state"] == "started"
