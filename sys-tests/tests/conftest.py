import uuid

import pytest
from sqlalchemy import create_engine, text
from tests import config
import httpx
from redis import Redis

from tests.config import app_url, redis_args


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(config.db_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def redis_client():
    client = Redis(**redis_args)
    yield client
    client.close()


@pytest.fixture(autouse=True)
def clean_db(db_engine, redis_client):
    with db_engine.connect() as conn:
        conn.execute(text("DELETE FROM review_decisions"))
        conn.execute(text("DELETE FROM approvals"))
        conn.execute(text("DELETE FROM experiments_latest"))
        conn.execute(text("DELETE FROM experiments_history"))
        conn.execute(text("DELETE FROM flags"))
        conn.execute(text("DELETE FROM assigned_approvers"))
        conn.execute(text("DELETE FROM users"))
        conn.commit()
    #redis_client.flushdb()


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
def create_admin_in_db(create_user_in_db):
    return lambda email, iap_id=None: create_user_in_db(
        email=email, role="ADMIN", iap_id=iap_id
    )


@pytest.fixture
def create_default_admin_in_db(create_admin_in_db):
    return create_admin_in_db("admin@t.ru", "admin")


@pytest.fixture
def create_default_experimenter_in_db(create_experimenter_in_db):
    return create_experimenter_in_db("exp@t.ru", "exp")


DEFAULT_ADMIN_LOGIN = {
    "X-User-Id": "admin",
    "X-User-Email": "admin@t.ru",
}


DEFAULT_EXPERIMENTER_LOGIN = {
    "X-User-Id": "exp",
    "X-User-Email": "exp@t.ru",
}


@pytest.fixture
def create_experimenter_in_db(create_user_in_db):
    return lambda email, iap_id=None: create_user_in_db(
        email=email, role="EXPERIMENTER", iap_id=iap_id
    )


@pytest.fixture
def create_approver_in_db(create_user_in_db):
    return lambda email, iap_id=None: create_user_in_db(
        email=email, role="APPROVER", iap_id=iap_id
    )


@pytest.fixture
def create_viewer_in_db(create_user_in_db):
    return lambda email, iap_id=None: create_user_in_db(
        email=email, role="VIEWER", iap_id=iap_id
    )


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
            f"{app_url}/api/v1/accounts/user/by-email",
            params={"email": email},
            headers=headers
        )
    return _get
