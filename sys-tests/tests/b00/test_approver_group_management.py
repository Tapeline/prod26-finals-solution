from tests.client import iap_login
import httpx

from tests.config import app_url


def test_admin_can_set_approver_group(
    create_user_in_db,
    get_user_from_db,
    get_user_by_email
):
    admin_iap = "001"
    admin_email = "admin@t.ru"
    create_user_in_db(admin_email, "ADMIN", admin_iap)
    experimenter = create_user_in_db("exp@t.ru", "EXPERIMENTER", None)
    approver1 = create_user_in_db("a1@t.ru", "APPROVER", None)
    approver2 = create_user_in_db("a2@t.ru", "APPROVER", None)

    response = httpx.put(
        f"{app_url}/api/v1/accounts/experimenter/"
        f"{experimenter['id']}/approver-group",
        json={
            "approver_ids": [approver1["id"], approver2["id"]],
            "threshold": 1
        },
        headers=iap_login(admin_iap, admin_email)
    )

    assert response.status_code == 200
    json = response.json()
    assert set(json["approver_ids"]) == {approver1["id"], approver2["id"]}
    assert json["threshold"] == 1
