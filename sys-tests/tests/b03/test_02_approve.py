import httpx

from tests.helpers import (
    create_experiment, set_approver_group,
    send_to_review, create_flag, get_experiment,
)
from tests.client import iap_login
from tests.config import app_url
from tests.conftest import DEFAULT_ADMIN_LOGIN


def test_transition_in_review_to_approved(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
    create_approver_in_db
):
    user_exp = create_default_experimenter_in_db
    appr_email, appr_iap = "appr@t.ru", "iap-appr"
    user_appr = create_approver_in_db(appr_email, appr_iap)
    set_approver_group(user_exp["id"], [user_appr["id"]], threshold=1)
    create_flag()
    exp = create_experiment()
    send_to_review(exp["id"])

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/approve",
        headers=iap_login(appr_iap, appr_email)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert get_experiment(exp["id"])["state"] == "accepted"


def test_approval_threshold_logic(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
    create_approver_in_db,
):
    appr1_email, appr1_iap = "a1@t.ru", "iap-a1"
    appr2_email, appr2_iap = "a2@t.ru", "iap-a2"
    user_exp = create_default_experimenter_in_db
    u_a1 = create_approver_in_db(appr1_email, appr1_iap)
    u_a2 = create_approver_in_db(appr2_email, appr2_iap)
    set_approver_group(user_exp["id"], [u_a1["id"], u_a2["id"]], threshold=2)
    create_flag()
    exp = create_experiment()
    send_to_review(exp["id"])

    resp1 = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/approve",
        headers=iap_login(appr1_iap, appr1_email)
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "waiting_for_more_votes"

    resp2 = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/approve",
        headers=iap_login(appr2_iap, appr2_email)
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "accepted"


def test_transition_in_review_to_approved_when_no_group(
    create_default_admin_in_db,
    create_default_experimenter_in_db,
):
    create_flag()
    exp = create_experiment()
    send_to_review(exp["id"])

    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp['id']}/approve",
        headers=DEFAULT_ADMIN_LOGIN
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

