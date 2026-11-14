from datetime import datetime, timezone

import pytest
from starlette.websockets import WebSocketDisconnect

from app.clock import FixedClock
from app.main import app
from app.telemetry import TelemetryHub, get_hub

SAMPLE = {
    "robot_state": "A_CAMINHO",
    "pose": {"x": 14.2, "y": 28.9, "yaw": 0.0},
    "battery": 99.1,
    "delivery_id": 7,
    "route": [{"x": 14.2, "y": 28.9}, {"x": 20.0, "y": 28.9}],
    "obstacles": [{"x": 18.0, "y": 28.9, "radius": 0.4}],
    "updated_at": "2020-01-01T00:00:00+00:00",
}
NOW = datetime(2026, 11, 13, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def hub(client):
    fresh = TelemetryHub(FixedClock(NOW))
    app.dependency_overrides[get_hub] = lambda: fresh
    yield fresh
    app.dependency_overrides.pop(get_hub, None)


def test_before_any_telemetry_the_panel_gets_a_no_signal_snapshot(client, auth, hub):
    r = client.get("/telemetry", headers=auth("medico1"))
    assert r.status_code == 200
    body = r.json()
    assert (body["robot_state"], body["battery"], body["route"], body["obstacles"]) == ("IDLE", 0, [], [])
    assert body["updated_at"].startswith("1970-01-01")


def test_robot_posts_and_everyone_logged_in_reads_the_last_state(client, auth, hub):
    assert client.post("/robot/telemetry", json=SAMPLE, headers=auth("robo")).status_code == 204
    body = client.get("/telemetry", headers=auth("medico1")).json()
    assert body["robot_state"] == "A_CAMINHO" and body["delivery_id"] == 7
    assert body["route"] == SAMPLE["route"] and body["obstacles"] == SAMPLE["obstacles"]


def test_the_backend_ignores_the_robots_updated_at_and_stamps_the_receipt_time(client, auth, hub):
    client.post("/robot/telemetry", json=SAMPLE, headers=auth("robo"))
    assert client.get("/telemetry", headers=auth("medico1")).json()["updated_at"] == "2026-11-13T15:00:00Z"


def test_optional_fields_default_to_empty(client, auth, hub):
    minimal = {"robot_state": "IDLE", "pose": {"x": 6.5, "y": 26.5, "yaw": -1.5708}, "battery": 100}
    assert client.post("/robot/telemetry", json=minimal, headers=auth("robo")).status_code == 204
    body = client.get("/telemetry", headers=auth("medico1")).json()
    assert (body["delivery_id"], body["route"], body["obstacles"]) == (None, [], [])


@pytest.mark.parametrize(
    "change",
    [
        {"robot_state": "VOANDO"},
        {"battery": 101},
        {"battery": -1},
        {"pose": {"x": 1, "y": 1}},
        {"pose": {"x": 1e9, "y": 1, "yaw": 0}},
        {"route": [{"x": 0, "y": 0}] * 51},
        {"obstacles": [{"x": 0, "y": 0, "radius": 0.3}] * 21},
        {"obstacles": [{"x": 0, "y": 0, "radius": -1}]},
    ],
)
def test_invalid_bodies_are_422_and_leave_the_last_state_alone(client, auth, hub, change):
    r = client.post("/robot/telemetry", json={**SAMPLE, **change}, headers=auth("robo"))
    assert r.status_code == 422
    assert client.get("/telemetry", headers=auth("medico1")).json()["robot_state"] == "IDLE"


def test_roles_and_authentication(client, auth, hub):
    assert client.post("/robot/telemetry", json=SAMPLE).status_code == 401
    for user in ("medico1", "admin", "farmaceutico1"):
        assert client.post("/robot/telemetry", json=SAMPLE, headers=auth(user)).status_code == 403
    assert client.get("/telemetry").status_code == 401


def test_websocket_sends_the_current_state_and_then_every_update(client, auth, hub):
    token = auth("medico1")["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/ws/telemetry?token={token}") as ws:
        assert ws.receive_json()["robot_state"] == "IDLE"
        client.post("/robot/telemetry", json=SAMPLE, headers=auth("robo"))
        pushed = ws.receive_json()
        assert pushed["robot_state"] == "A_CAMINHO" and pushed["updated_at"] == "2026-11-13T15:00:00Z"
        assert pushed == client.get("/telemetry", headers=auth("medico1")).json()
    assert hub._observers == []  # a conexão fechou e saiu da lista de assinantes


def test_websocket_accepts_the_token_in_the_authorization_header(client, auth, hub):
    with client.websocket_connect("/ws/telemetry", headers=auth("medico1")) as ws:
        assert ws.receive_json()["robot_state"] == "IDLE"


@pytest.mark.parametrize("query", ["", "?token=lixo"])
def test_websocket_without_a_valid_token_is_refused(client, hub, query):
    # o handshake é aceito antes de fechar: recusado no handshake, o navegador só veria 1006, nunca o 1008
    with client.websocket_connect(f"/ws/telemetry{query}") as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 1008
