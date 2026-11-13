import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Role

REQUESTERS = ("medico", "enfermeiro", "farmaceutico", "admin")


def token(user_id: int = 1, **over) -> str:
    claims = {"sub": str(user_id), "role": "medico", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "jti": uuid.uuid4().hex}
    claims.update(over)
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def get_me(client, bearer: str) -> int:
    return client.get("/me", headers={"Authorization": f"Bearer {bearer}"}).status_code


def test_a_correctly_signed_token_with_the_right_role_works(client):
    assert get_me(client, token(1)) == 200  # o usuário 1 do seed é o medico1


def test_the_role_in_the_token_must_match_the_users_current_role(client):
    assert get_me(client, token(1, role="admin")) == 401  # medico1 com role admin forjada no claim


def test_a_non_numeric_subject_is_401_not_500(client):
    assert get_me(client, token(sub="abc")) == 401
    assert get_me(client, token(sub="9999")) == 401  # usuário que não existe


@pytest.mark.parametrize("claim", ["exp", "sub", "role", "jti"])
def test_every_required_claim_is_enforced(client, claim):
    claims = {"sub": "1", "role": "medico", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "jti": uuid.uuid4().hex}
    del claims[claim]
    assert get_me(client, jwt.encode(claims, settings.jwt_secret, algorithm="HS256")) == 401


def test_only_hs256_is_accepted_even_with_the_right_secret(client):
    claims = {"sub": "1", "role": "medico", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "jti": uuid.uuid4().hex}
    assert get_me(client, jwt.encode(claims, settings.jwt_secret, algorithm="HS512")) == 401


def test_the_server_refuses_to_start_with_a_short_secret():
    settings.jwt_secret = "curto"
    with pytest.raises(RuntimeError, match="GERALDO_JWT_SECRET"):
        with TestClient(app):
            pass


# (método, caminho, papéis permitidos). Quem não está na lista leva 403; sem token, 401.
PROTECTED = [
    ("post", "/deliveries", REQUESTERS),
    ("post", "/deliveries/1/cancel", REQUESTERS),
    ("post", "/deliveries/1/confirm-receipt", REQUESTERS),
    ("post", "/deliveries/1/approve", ("farmaceutico",)),
    ("post", "/robot/next-task", ("robo",)),
    ("post", "/robot/events", ("robo",)),
    ("post", "/robot/telemetry", ("robo",)),
    ("get", "/robot/estop", ("robo",)),
    ("post", "/robot/estop", ("admin", "farmaceutico")),
]
USERS = {"medico": "medico1", "enfermeiro": "enfermeiro1", "farmaceutico": "farmaceutico1", "admin": "admin", "robo": "robo"}


@pytest.mark.parametrize("method, path, allowed", PROTECTED)
def test_role_matrix(client, auth, method, path, allowed):
    assert client.request(method, path, json={}).status_code == 401
    for role in Role:
        if role.value not in allowed:
            status = client.request(method, path, json={}, headers=auth(USERS[role.value])).status_code
            assert status == 403, f"{role.value} em {method.upper()} {path} deveria levar 403, levou {status}"


def test_a_huge_numeric_subject_is_401_not_500(client):
    assert get_me(client, token(sub="9" * 40)) == 401  # estoura o inteiro do SQLite
