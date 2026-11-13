import json

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.errors import describe
from app.main import app
from tests.conftest import PASSWORD

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}


def detail_of(response) -> str:
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, str)  # o schema Error do contrato: detail é texto, não a lista do pydantic
    assert detail.startswith("Dados inválidos") and detail.endswith("Corrija e envie de novo.")
    return detail


def test_missing_fields_say_which_one(client):
    detail = detail_of(client.post("/auth/login", json={"username": "medico1"}))
    assert "password: campo obrigatório" in detail


def test_limits_are_explained_in_portuguese(client, auth):
    h = auth("medico1")
    assert "items.0.quantity: deve ser maior que 0" in detail_of(client.post("/deliveries", json={**BODY, "items": [{"item_id": "x", "quantity": 0}]}, headers=h))
    assert "deve ser no máximo 10000" in detail_of(client.post("/deliveries", json={**BODY, "items": [{"item_id": "x", "quantity": 10_001}]}, headers=h))
    assert "items: grande demais (máximo 50)" in detail_of(client.post("/deliveries", json={**BODY, "items": [{"item_id": "x", "quantity": 1}] * 51}, headers=h))
    assert "origin_id: grande demais (máximo 64)" in detail_of(client.post("/deliveries", json={**BODY, "origin_id": "a" * 65}, headers=h))
    assert "priority: valor fora da lista permitida" in detail_of(client.post("/deliveries", json={**BODY, "priority": "urgentissima"}, headers=h))
    assert "items: curto demais (mínimo 1)" in detail_of(client.post("/deliveries", json={**BODY, "items": []}, headers=h))


def test_huge_passwords_are_refused_before_hashing(client):
    assert "password: grande demais (máximo 128)" in detail_of(client.post("/auth/login", json={"username": "medico1", "password": "x" * 129}))


def test_malformed_json_is_422_not_500(client, auth):
    r = client.post("/deliveries", content="{isto não é json", headers={**auth("medico1"), "content-type": "application/json"})
    assert "o corpo não é um JSON válido" in detail_of(r)


def test_nan_in_the_telemetry_is_422_not_500(client, auth):
    sample = {"robot_state": "IDLE", "pose": {"x": 0, "y": 0, "yaw": 0}, "battery": 50}
    body = json.dumps({**sample, "battery": float("nan")})  # o Python escreve NaN, que não é JSON válido: o servidor aceita e recusa
    r = client.post("/robot/telemetry", content=body, headers={**auth("robo"), "content-type": "application/json"})
    assert "battery:" in detail_of(r)


def test_unknown_error_types_fall_back_to_a_generic_message():
    assert describe({"type": "coisa_nova", "loc": ("body", "x"), "msg": "?"}) == "x: valor inválido"


def test_unknown_path_and_wrong_method_are_portuguese(client, auth):
    r = client.get("/nao-existe", headers=auth("medico1"))
    assert r.status_code == 404 and "Confira a URL" in r.json()["detail"]
    r = client.delete("/me", headers=auth("medico1"))
    assert r.status_code == 405 and "Método não permitido" in r.json()["detail"]


def test_domain_errors_keep_their_own_message(client, auth):
    r = client.get("/deliveries/9999", headers=auth("medico1"))
    assert r.status_code == 404 and r.json()["detail"] == "Entrega não encontrada."


def test_unexpected_errors_do_not_leak_details(engine):
    def broken():
        raise RuntimeError("senha-do-banco=1234")
        yield  # pragma: no cover

    app.dependency_overrides[get_session] = broken
    try:
        r = TestClient(app, raise_server_exceptions=False).post("/auth/login", json={"username": "a", "password": PASSWORD})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 500
    assert "senha-do-banco" not in r.text and "Tente de novo" in r.json()["detail"]
