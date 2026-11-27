import pytest
from fakes import FakeGui, FakeRosPort
from geraldo_bridge.convert import RANGE_NAMES

try:
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    from geraldo_bridge.server import ALLOWED_ORIGINS, HOST, PORT, create_app
except ModuleNotFoundError:  # o pytest da raiz roda no Python do sistema, sem fastapi; um skip no topo derrubaria a coleta toda
    TestClient = WebSocketDisconnect = create_app = HOST = PORT = None
    ALLOWED_ORIGINS = ()

pytestmark = pytest.mark.skipif(TestClient is None, reason="a ponte precisa do fastapi: rode no venv do app")
from geraldo_bridge.state import BridgeState

BASE = "http://127.0.0.1:8765"
WS = "ws://127.0.0.1:8765/ws/sim"
SNAPSHOT_KEYS = {"robot_state", "pose", "battery", "route", "scan", "ranges", "estop", "stale", "updated_at"}


@pytest.fixture
def parts():
    state, port, gui = BridgeState(), FakeRosPort(), FakeGui()
    client = TestClient(create_app(state, port, gui, interval_s=0.01), base_url=BASE)
    return client, state, port, gui


def test_shutting_down_closes_the_gazebo_window_and_rclpy():
    # o uvicorn roda o lifespan no SIGTERM, mas não um finally em volta do uvicorn.run
    state, port, gui = BridgeState(), FakeRosPort(), FakeGui()
    with TestClient(create_app(state, port, gui), base_url=BASE):
        assert not gui.closed and not port.stopped
    assert gui.closed and port.stopped


def test_the_bridge_listens_only_on_loopback_on_port_8765():
    assert (HOST, PORT) == ("127.0.0.1", 8765)


def test_health(parts):
    client, *_ = parts
    assert client.get("/health").json() == {"status": "ok"}


def test_snapshot_returns_the_state(parts):
    client, state, *_ = parts
    state.update_robot_state("IDLE")
    body = client.get("/snapshot").json()
    assert set(body) == SNAPSHOT_KEYS
    assert body["robot_state"] == "IDLE"
    assert set(body["ranges"]) == set(RANGE_NAMES)


def test_estop_publishes_and_is_reflected_in_the_snapshot(parts):
    client, _, port, _ = parts
    res = client.post("/estop", json={"active": True})
    assert res.status_code == 204 and res.content == b""
    assert port.estop_published == [True]
    assert client.get("/snapshot").json()["estop"] is True
    client.post("/estop", json={"active": False})
    assert port.estop_published == [True, False]


@pytest.mark.parametrize("body", [{}, {"active": "talvez"}, {"active": None}])
def test_estop_rejects_a_body_without_a_boolean(parts, body):
    client, _, port, _ = parts
    assert client.post("/estop", json=body).status_code == 422
    assert port.estop_published == []


def test_open_gazebo_returns_the_pid(parts):
    client, *_, gui = parts
    res = client.post("/gazebo/gui")
    assert res.status_code == 202
    assert res.json() == {"pid": 4321, "already_running": False}
    assert client.post("/gazebo/gui").json() == {"pid": 4321, "already_running": True}


def test_open_gazebo_failure_is_a_500_with_the_message():
    state, port = BridgeState(), FakeRosPort()
    client = TestClient(create_app(state, port, FakeGui(error="Gazebo não instalado. Instale o Gazebo Harmonic.")), base_url=BASE)
    res = client.post("/gazebo/gui")
    assert res.status_code == 500
    assert res.json() == {"detail": "Gazebo não instalado. Instale o Gazebo Harmonic."}


def test_a_foreign_host_header_is_refused(parts):
    client, *_ = parts
    assert client.get("/health", headers={"host": "evil.example:8765"}).status_code == 400


def test_a_foreign_origin_is_refused_before_reaching_the_handler(parts):
    client, _, port, gui = parts
    assert client.get("/snapshot", headers={"origin": "http://evil.example"}).status_code == 403
    assert client.post("/estop", json={"active": True}, headers={"origin": "http://evil.example"}).status_code == 403
    assert client.post("/gazebo/gui", headers={"origin": "http://evil.example"}).status_code == 403
    assert port.estop_published == [] and gui.opened == 0


@pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
def test_the_app_origins_get_cors_headers(parts, origin):
    client, *_ = parts
    res = client.get("/snapshot", headers={"origin": origin})
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == origin


def test_preflight_from_the_app_is_accepted(parts):
    client, *_ = parts
    res = client.options(
        "/estop",
        headers={"origin": ALLOWED_ORIGINS[0], "access-control-request-method": "POST", "access-control-request-headers": "content-type"},
    )
    assert res.status_code == 200


def test_websocket_streams_snapshots(parts):
    client, state, *_ = parts
    state.update_battery(66.0)
    with client.websocket_connect(WS) as ws:
        first = ws.receive_json()
        second = ws.receive_json()
    assert set(first) == SNAPSHOT_KEYS
    assert first["battery"] == second["battery"] == 66.0


def test_websocket_refuses_a_foreign_origin(parts):
    client, *_ = parts
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(WS, headers={"origin": "http://evil.example"}):
            pass


def test_the_bridge_exposes_exactly_these_routes_and_no_cmd_vel(parts):
    client, *_ = parts
    paths = {r.path for r in client.app.routes}
    assert paths == {"/health", "/snapshot", "/estop", "/gazebo/gui", "/ws/sim"}
