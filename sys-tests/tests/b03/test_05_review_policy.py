import pytest
import httpx

from tests.b03.helpers import (
     set_approver_group,
    create_flag, create_experiment, send_to_review,
)
from tests.client import iap_login
from tests.config import app_url


# TODO: others should be tested in unit tests


def test_review_policy_enforcement(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
    create_approver_in_db
):
    user_exp = create_default_experimenter_in_db

    valid_appr = create_approver_in_db("valid@t.ru", "iap-valid")
    create_approver_in_db("stranger@t.ru", "iap-stranger")

    set_approver_group(user_exp["id"], [valid_appr["id"]], threshold=1)

    create_flag()
    exp = create_experiment()
    send_to_review(exp["id"])

    resp_invalid = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/approve",
        headers=iap_login("iap-stranger", "stranger@t.ru")
    )
    assert resp_invalid.status_code == 403
