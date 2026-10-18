import os

os.environ.setdefault("BCRYPT_ROUNDS", "4")  # hash rápido, solo en tests

import mongomock  # noqa: E402
import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import limiter  # noqa: E402
from app.utils.database import crear_indices, seed_usuarios  # noqa: E402


@pytest.fixture
def app():
    db = mongomock.MongoClient()["pami_test"]
    crear_indices(db)
    seed_usuarios(db)
    app = create_app(TestConfig, db=db)
    limiter.reset()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def _login(email, password):
        return client.post("/api/auth/login", json={"email": email, "password": password})

    return _login


@pytest.fixture
def auth_headers(login):
    def _headers(email, password):
        token = login(email, password).get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers
