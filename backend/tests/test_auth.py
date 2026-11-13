import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.security import decode_token
from tests.conftest import PASSWORD


def forge(payload: dict, key: str, algorithm: str) -> dict:
    return {"Authorization": f"Bearer {jwt.encode(payload, key, algorithm=algorithm)}"}


def valid_payload(**over) -> dict:
    base = {
        "sub": "1",
        "role": "medico",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "jti": uuid.uuid4().hex,
    }
    base.update(over)
    return base


def test_login_returns_a_bearer_token_with_the_contract_claims(client):
    r = client.post("/auth/login", json={"username": "medico1", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    claims = decode_token(body["access_token"])
    assert set(claims) >= {"sub", "role", "exp", "jti"}
    assert claims["role"] == "medico"


def test_login_rejects_wrong_password_and_unknown_user(client):
    for body in ({"username": "medico1", "password": "errada"}, {"username": "ninguem", "password": PASSWORD}):
        r = client.post("/auth/login", json=body)
        assert r.status_code == 401
        assert "senha" in r.json()["detail"].lower()


def test_me_returns_role_and_default_location(client, auth):
    r = client.get("/me", headers=auth("medico1"))
    assert r.status_code == 200
    assert r.json() == {"id": r.json()["id"], "username": "medico1", "role": "medico", "local_id": "consultorio1"}


def test_me_without_token_is_401(client):
    assert client.get("/me").status_code == 401


def test_expired_token_is_401(client):
    settings.jwt_minutes = -1
    headers = {"Authorization": "Bearer " + client.post("/auth/login", json={"username": "medico1", "password": PASSWORD}).json()["access_token"]}
    assert client.get("/me", headers=headers).status_code == 401


def test_token_with_none_algorithm_is_rejected(client):
    assert client.get("/me", headers=forge(valid_payload(), "", "none")).status_code == 401


def test_token_signed_with_another_secret_is_rejected(client):
    other = "outro-segredo-com-mais-de-32-bytes-9876543210"
    assert client.get("/me", headers=forge(valid_payload(), other, "HS256")).status_code == 401


def test_token_without_jti_is_rejected(client):
    payload = valid_payload()
    del payload["jti"]
    assert client.get("/me", headers=forge(payload, settings.jwt_secret, "HS256")).status_code == 401


def test_garbage_token_is_401(client):
    assert client.get("/me", headers={"Authorization": "Bearer isto-nao-e-jwt"}).status_code == 401
