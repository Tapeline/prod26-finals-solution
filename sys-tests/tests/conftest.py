import uuid

import pytest
from sqlalchemy import create_engine, text
from tests import config
import httpx

from tests.config import app_url


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(config.db_url)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(db_engine):
    with db_engine.connect() as conn:
        conn.execute(text("DELETE FROM assigned_approvers"))
        conn.execute(text("DELETE FROM users"))
        conn.commit()


@pytest.fixture
def create_user_in_db(db_engine):
    def _create(email: str, role: str, iap_id: str = None):
        user_id = str(uuid.uuid4())
        query = text(
            """
            INSERT INTO users (id, email, role, iap_id)
            VALUES (:id, :email, :role, :iap_id)
            """
        )
        with db_engine.connect() as conn:
            conn.execute(
                query, {
                    "id": user_id,
                    "email": email,
                    "role": role,
                    "iap_id": iap_id
                }
            )
            conn.commit()
        return {"id": user_id, "email": email, "role": role, "iap_id": iap_id}

    return _create


@pytest.fixture
def get_user_from_db(db_engine):
    def _get(email: str):
        query = text("SELECT * FROM users WHERE email = :email")
        with db_engine.connect() as conn:
            result = conn.execute(query, {"email": email}).fetchone()
            if result:
                return result._mapping
            return None
    return _get


@pytest.fixture
def get_user_by_email():
    def _get(email: str, headers):
        return httpx.get(
            f"{app_url}/api/v1/account/user/by-email",
            params={"email": email},
            headers=headers
        )
    return _get
