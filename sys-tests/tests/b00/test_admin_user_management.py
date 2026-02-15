from tests.client import iap_login
import httpx

from tests.config import app_url


def test_admin_can_create_user(
    create_user_in_db,
    get_user_from_db,
    get_user_by_email
):
    admin_iap = "iap-admin-01"
    admin_email = "admin@t.ru"
    create_user_in_db(
        email=admin_email, role="ADMIN", iap_id=admin_iap
    )
    new_user_email = "some-new-user@t.ru"
    new_user_role = "viewer"

    response = httpx.post(
        f"{app_url}/api/v1/account/create",
        json={
            "email": new_user_email,
            "role": new_user_role
        },
        headers=iap_login(admin_iap, admin_email)
    )
    assert response.status_code == 201

    new_user = get_user_by_email(
        new_user_email, iap_login(admin_iap, admin_email)
    ).raise_for_status().json()
    assert new_user["email"] == new_user_email
    assert new_user["role"] == new_user_role


def test_regular_user_cannot_create_user(create_user_in_db):
    user_email = "viewer@t.ru"
    user_iap = "iap-obs-01"
    create_user_in_db(
        email=user_email, role="VIEWER", iap_id=user_iap
    )

    response = httpx.post(
        f"{app_url}/api/v1/account/create",
        json={"email": "admin@t.ru", "role": "admin"},
        headers=iap_login(user_iap, user_email)
    )

    assert response.status_code == 403
