"""Teste de contrato: o backend responde o que docs/contracts/openapi.yaml promete.

1. As operações do contrato e as do backend são as mesmas, com os mesmos códigos de sucesso.
2. Um roteiro chama CADA operação (sucesso e erros) e valida o status e o corpo de cada resposta
   contra o schema do contrato (campos a mais ou a menos, tipos, enums, nulos e limites).
"""
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

from app.estop import EstopStore, get_estop
from app.main import app
from app.telemetry import TelemetryHub, get_hub
from tests.conftest import PASSWORD

CONTRACT_FILE = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "openapi.yaml"
SPEC = yaml.safe_load(CONTRACT_FILE.read_text(encoding="utf-8"))
METHODS = {"get", "post", "put", "delete", "patch"}


def norm(path: str) -> str:
    """Compara rotas ignorando o nome do parâmetro de caminho ({id} x {delivery_id})."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def operations(spec: dict) -> dict:
    return {(m, norm(p)): op for p, ops in spec["paths"].items() for m, op in ops.items() if m in METHODS}


def success_codes(op: dict) -> list[str]:
    return sorted(str(code) for code in op["responses"] if str(code).startswith("2"))


CONTRACT = operations(SPEC)

FORMATS = jsonschema.FormatChecker()


@FORMATS.checks("date-time")
def _is_rfc3339(value) -> bool:
    """date-time do contrato = RFC 3339: precisa de offset (Z ou +hh:mm); hora sem fuso o navegador lê como local."""
    return not isinstance(value, str) or bool(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)", value))


def to_jsonschema(node, strict: bool = True):
    """OpenAPI 3.0 -> JSON Schema: resolve $ref, trata nullable e proíbe campos que o contrato não lista."""
    if isinstance(node, list):
        return [to_jsonschema(item, strict) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return to_jsonschema(resolve(node["$ref"]), strict)
    out = {}
    for key, value in node.items():
        if key in ("nullable", "example", "description"):
            continue
        if key == "allOf":  # o RobotTask soma campos ao Delivery: cada parte, sozinha, não pode ser estrita
            out[key] = [to_jsonschema(part, strict=False) for part in value]
        elif key == "properties":
            out[key] = {name: to_jsonschema(child) for name, child in value.items()}
        elif key == "items":
            out[key] = to_jsonschema(value)
        else:
            out[key] = value
    if node.get("nullable"):
        out["type"] = [out["type"], "null"]
        if "enum" in out:
            out["enum"] = [*out["enum"], None]
    if strict and "properties" in node and "allOf" not in node:
        out["additionalProperties"] = False
    return out


def resolve(ref: str) -> dict:
    node = SPEC
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def response_schema(op: dict, status: int):
    declared = op["responses"].get(str(status)) or op["responses"].get(status)
    assert declared is not None, f"o contrato não declara o status {status} (declarados: {sorted(map(str, op['responses']))})"
    if "$ref" in declared:
        declared = resolve(declared["$ref"])
    content = declared.get("content", {}).get("application/json")
    return to_jsonschema(content["schema"]) if content else None


class Probe:
    """Faz a chamada, confere o status esperado e valida o corpo contra o contrato."""

    def __init__(self, client, auth) -> None:
        self._client, self._auth = client, auth
        self.seen: set[tuple[str, str, int]] = set()

    def __call__(self, method: str, template: str, *, expect: int, as_: str | None = None, json=None, params=None, **path):
        url = template.format(**path)
        response = self._client.request(method, url, json=json, params=params, headers=self._auth(as_) if as_ else {})
        assert response.status_code == expect, f"{method.upper()} {url}: esperado {expect}, veio {response.status_code}: {response.text}"
        schema = response_schema(CONTRACT[(method, norm(template))], expect)
        if expect == 204:
            assert response.content == b"", f"{method.upper()} {url}: o contrato prevê 204 sem corpo, mas veio {response.text!r}"
        else:  # resposta sem schema próprio no contrato (ex.: o 422 do telemetry) segue o schema Error
            jsonschema.Draft7Validator(schema or to_jsonschema(SPEC["components"]["schemas"]["Error"]), format_checker=FORMATS).validate(response.json())
        self.seen.add((method, norm(template), expect))
        return response


def test_the_backend_exposes_exactly_the_contract_operations():
    implemented = operations(app.openapi())
    assert set(CONTRACT) - set(implemented) == set(), "operações do contrato que o backend não tem"
    assert set(implemented) - set(CONTRACT) == set(), "operações do backend que não estão no contrato"


def test_success_status_codes_follow_the_contract():
    implemented = operations(app.openapi())
    for key, op in CONTRACT.items():
        assert success_codes(implemented[key]) == success_codes(op), key


@pytest.fixture
def fresh_state(client):
    hub, estop = TelemetryHub(), EstopStore()
    app.dependency_overrides[get_hub] = lambda: hub
    app.dependency_overrides[get_estop] = lambda: estop
    yield
    app.dependency_overrides.pop(get_hub, None)
    app.dependency_overrides.pop(get_estop, None)


MEDIA = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}
CRITICA = {"origin_id": "banco_sangue", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], "priority": "critica"}
TELEMETRY = {"robot_state": "A_CAMINHO", "pose": {"x": 14.2, "y": 28.9, "yaw": 0.0}, "battery": 99.1, "delivery_id": 7,
             "route": [{"x": 14.2, "y": 28.9}], "obstacles": [{"x": 18.0, "y": 28.9, "radius": 0.4}]}


def event(delivery_id: int, name: str) -> dict:
    return {"delivery_id": delivery_id, "event": name}


def test_every_response_matches_the_contract(client, auth, fresh_state):
    api = Probe(client, auth)

    api("post", "/auth/login", json={"username": "medico1", "password": PASSWORD}, expect=200)
    api("post", "/auth/login", json={"username": "medico1", "password": "errada"}, expect=401)
    api("get", "/me", as_="medico1", expect=200)
    api("get", "/me", expect=401)
    api("get", "/locations", as_="medico1", expect=200)
    api("get", "/locations", expect=401)
    api("get", "/stock", as_="medico1", expect=200)
    api("get", "/stock", as_="medico1", params={"location_id": "farmacia"}, expect=200)
    api("get", "/stock", expect=401)

    # criar, listar e consultar
    media = api("post", "/deliveries", as_="medico1", json=MEDIA, expect=201).json()["id"]
    api("post", "/deliveries", as_="medico1", json={**MEDIA, "items": [{"item_id": "dipirona-500mg", "quantity": 9999}]}, expect=409)
    api("post", "/deliveries", as_="medico1", json={**MEDIA, "items": []}, expect=422)
    api("post", "/deliveries", as_="robo", json=MEDIA, expect=403)
    api("post", "/deliveries", json=MEDIA, expect=401)
    api("get", "/deliveries", as_="medico1", expect=200)
    api("get", "/deliveries", expect=401)
    api("get", "/deliveries/{id}", as_="medico1", id=media, expect=200)
    api("get", "/deliveries/{id}", as_="robo", id=media, expect=200)
    api("get", "/deliveries/{id}", as_="medico1", id=9999, expect=404)
    api("get", "/deliveries/{id}", id=media, expect=401)

    # assinatura dupla da crítica
    critica = api("post", "/deliveries", as_="medico1", json=CRITICA, expect=201).json()
    assert critica["status"] == "PENDENTE_APROVACAO"
    api("post", "/deliveries/{id}/approve", as_="medico1", id=critica["id"], expect=403)
    api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=9999, expect=404)
    api("post", "/deliveries/{id}/approve", id=critica["id"], expect=401)
    assert api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=critica["id"], expect=200).json()["status"] == "NA_FILA"
    api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=critica["id"], expect=409)

    # cancelar
    to_cancel = api("post", "/deliveries", as_="medico2", json=MEDIA, expect=201).json()["id"]
    api("post", "/deliveries/{id}/cancel", as_="robo", id=to_cancel, expect=403)
    api("post", "/deliveries/{id}/cancel", id=to_cancel, expect=401)
    api("post", "/deliveries/{id}/cancel", as_="admin", id=9999, expect=404)
    assert api("post", "/deliveries/{id}/cancel", as_="medico2", id=to_cancel, expect=200).json()["status"] == "CANCELADA"
    api("post", "/deliveries/{id}/cancel", as_="medico2", id=to_cancel, expect=409)

    # o robô: fila (crítica antes da média), eventos
    api("post", "/robot/next-task", as_="medico1", expect=403)
    api("post", "/robot/next-task", expect=401)
    first = api("post", "/robot/next-task", as_="robo", expect=200).json()
    second = api("post", "/robot/next-task", as_="robo", expect=200).json()
    assert (first["id"], second["id"]) == (critica["id"], media)
    assert second["origin_waypoint"] == "farmacia_balcao" and second["dest_waypoint"] == "cons1_entrega"
    api("post", "/robot/next-task", as_="robo", expect=204)

    api("post", "/robot/events", as_="robo", json=event(media, "LOADED"), expect=200)
    api("post", "/robot/events", as_="robo", json=event(media, "ARRIVED"), expect=200)
    api("post", "/robot/events", as_="robo", json=event(media, "ARRIVED"), expect=409)
    api("post", "/robot/events", as_="robo", json=event(9999, "LOADED"), expect=404)
    api("post", "/robot/events", as_="medico1", json=event(media, "LOADED"), expect=403)
    api("post", "/robot/events", json=event(media, "LOADED"), expect=401)
    api("post", "/robot/events", as_="robo", json={**event(critica["id"], "FAILED"), "reason": "não chegou à origem"}, expect=200)

    # confirmar o recebimento
    api("post", "/deliveries/{id}/confirm-receipt", id=media, expect=401)
    api("post", "/deliveries/{id}/confirm-receipt", as_="robo", id=media, expect=403)
    api("post", "/deliveries/{id}/confirm-receipt", as_="medico1", id=9999, expect=404)
    assert api("post", "/deliveries/{id}/confirm-receipt", as_="medico1", id=media, expect=200).json()["status"] == "ENTREGUE"
    api("post", "/deliveries/{id}/confirm-receipt", as_="medico1", id=media, expect=409)
    api("post", "/robot/events", as_="robo", json=event(media, "UNLOCKED"), expect=200)

    # histórico
    api("get", "/movements", as_="admin", expect=200)
    api("get", "/movements", as_="admin", params={"delivery_id": media, "location_id": "farmacia"}, expect=200)
    api("get", "/movements", expect=401)

    # telemetria e emergência
    api("post", "/robot/telemetry", as_="robo", json=TELEMETRY, expect=204)
    api("post", "/robot/telemetry", as_="robo", json={**TELEMETRY, "battery": 150}, expect=422)
    api("post", "/robot/telemetry", as_="medico1", json=TELEMETRY, expect=403)
    api("post", "/robot/telemetry", json=TELEMETRY, expect=401)
    assert api("get", "/telemetry", as_="medico1", expect=200).json()["robot_state"] == "A_CAMINHO"
    api("get", "/telemetry", expect=401)

    api("post", "/robot/estop", as_="admin", json={"active": True}, expect=204)
    api("post", "/robot/estop", as_="admin", json={"active": "talvez"}, expect=422)
    api("post", "/robot/estop", as_="medico1", json={"active": True}, expect=403)
    api("post", "/robot/estop", json={"active": True}, expect=401)
    assert api("get", "/robot/estop", as_="robo", expect=200).json() == {"active": True}
    api("get", "/robot/estop", as_="medico1", expect=403)
    api("get", "/robot/estop", expect=401)

    exercised = {(method, path) for method, path, _ in api.seen}
    assert exercised == set(CONTRACT), f"operações que o roteiro não chamou: {set(CONTRACT) - exercised}"
    declared = {(m, p, int(code)) for (m, p), op in CONTRACT.items() for code in success_codes(op)}
    assert declared <= api.seen, f"códigos de sucesso que o roteiro não viu: {declared - api.seen}"


def test_the_websocket_pushes_the_telemetry_schema(client, auth, fresh_state):
    schema = to_jsonschema(SPEC["components"]["schemas"]["Telemetry"])
    token = auth("medico1")["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/ws/telemetry?token={token}") as ws:
        jsonschema.Draft7Validator(schema).validate(ws.receive_json())
        client.post("/robot/telemetry", json=TELEMETRY, headers=auth("robo"))
        pushed = ws.receive_json()
        jsonschema.Draft7Validator(schema).validate(pushed)
        assert pushed["robot_state"] == "A_CAMINHO"
