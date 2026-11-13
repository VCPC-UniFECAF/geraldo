import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.api import BackendClient  # noqa: E402
from robot.scripts.fake_backend import DEMO_TASKS, FakeBackend  # noqa: E402


@pytest.fixture
def backend():
    server = FakeBackend([dict(t) for t in DEMO_TASKS]).start()
    yield server
    server.stop()


@pytest.fixture
def client(backend):
    c = BackendClient(backend.url, "robo", "robo-local")
    c.login()
    return c


def test_send_event_posts_the_contract_body(backend, client):
    assert client.send_event(1, "FAILED", "não chegou à origem") is True
    assert backend.events == [{"delivery_id": 1, "event": "FAILED", "reason": "não chegou à origem"}]


def test_send_event_without_reason_sends_null(backend, client):
    client.send_event(1, "LOADED")
    assert backend.events[0]["reason"] is None


def test_send_event_returns_false_when_the_backend_answers_409(backend, client):
    backend.reject_events = True
    assert client.send_event(1, "UNLOCKED") is False


def test_delivery_status_waits_then_turns_delivered(backend, client):
    assert client.delivery_status(1) == "AGUARDANDO_RECEBIMENTO"
    assert client.delivery_status(1) == "ENTREGUE"


def test_send_telemetry_posts_the_body(backend, client):
    client.send_telemetry({"robot_state": "IDLE", "battery": 100})
    assert backend.telemetry == [{"robot_state": "IDLE", "battery": 100}]


def test_new_calls_log_in_again_when_the_token_expires(backend, client):
    backend.expire_token()
    assert client.delivery_status(1) == "AGUARDANDO_RECEBIMENTO"
    backend.expire_token()
    client.send_telemetry({"robot_state": "IDLE"})
    assert backend.calls.count("/auth/login") == 3
