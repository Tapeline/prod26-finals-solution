from tests.client import iap_login
from tests.config import app_url
import httpx


def test_activate_existing_user(create_user_in_db):
    email = "exp@t.ru"
    user_iap_id = "iap-12345"

    create_user_in_db(email=email, role="EXPERIMENTER", iap_id=None)

    response = httpx.get(
        f"{app_url}/api/v1/accounts/activate",
        headers=iap_login(user_iap_id, email)
    )

    assert response.status_code == 200
    assert response.json()["iap_id"] == user_iap_id
