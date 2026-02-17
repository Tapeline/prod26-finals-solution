import httpx

from tests.b03.helpers import create_experiment, create_flag
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN


def test_transition_draft_to_in_review(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
):
    create_flag()
    exp = create_experiment()

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/send-to-review",
        headers=DEFAULT_EXPERIMENTER_LOGIN,
    )

    assert response.status_code == 200
    assert response.json()["state"] == "in_review"
