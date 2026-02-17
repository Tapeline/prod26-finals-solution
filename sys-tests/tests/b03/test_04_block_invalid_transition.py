import httpx

from tests.helpers import (
    create_flag, create_experiment,
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
