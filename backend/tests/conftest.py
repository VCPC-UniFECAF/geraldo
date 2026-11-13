from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.db import create_db, get_session, make_engine
from app.main import app
from app.seed import seed

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
PASSWORD = "senha-de-teste"


@pytest.fixture(autouse=True)
def test_settings():
    names = ("jwt_secret", "jwt_minutes", "demo_password", "password_iterations", "auto_seed")
    old = {n: getattr(settings, n) for n in names}
    settings.jwt_secret = "segredo-de-teste-com-mais-de-32-bytes-0123456789"
    settings.jwt_minutes = 60
    settings.demo_password = PASSWORD
    settings.password_iterations = 1000
    settings.auto_seed = False
    yield
    for n, v in old.items():
        setattr(settings, n, v)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    create_db(eng)
    with Session(eng) as s:
        seed(s, FIXTURES)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    def login(username: str) -> dict:
        r = client.post("/auth/login", json={"username": username, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return login
