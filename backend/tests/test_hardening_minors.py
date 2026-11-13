import asyncio
from datetime import datetime

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session

from app.db import get_session
from app.errors import describe, install
from app.main import app
from app.routers.telemetry import _Subscriber
from app.schemas import PoseIn, RobotState, TelemetryOut
from datetime import timezone


def telemetry(battery: float) -> TelemetryOut:
    return TelemetryOut(robot_state=RobotState.IDLE, pose=PoseIn(x=0, y=0, yaw=0), battery=battery, updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_websocket_releases_the_db_session_right_after_authenticating(client, auth, engine):
    closed = []

    def tracking():
        with Session(engine) as s:
            original = s.close
            s.close = lambda: (closed.append(True), original())[1]
            yield s

    token = auth("medico1")["Authorization"].split()[1]
    app.dependency_overrides[get_session] = tracking  # só depois do login, que também usa a sessão
    with client.websocket_connect(f"/ws/telemetry?token={token}") as ws:
        ws.receive_json()
        assert closed  # fechada com o socket ainda aberto
    app.dependency_overrides.pop(get_session, None)


def test_subscriber_survives_a_closed_socket_loop():
    async def make():
        return _Subscriber()

    loop = asyncio.new_event_loop()
    sub = loop.run_until_complete(make())
    loop.close()
    sub.update(telemetry(1))  # não pode levantar RuntimeError e derrubar o POST do robô


def test_subscriber_queue_is_bounded_and_drops_the_oldest():
    async def run():
        sub = _Subscriber()
        for i in range(500):
            sub.update(telemetry(i % 100))
        await asyncio.sleep(0.05)
        return sub.queue

    queue = asyncio.run(run())
    assert 0 < queue.maxsize < 500 and queue.qsize() == queue.maxsize


def error_of(type_, value):
    with pytest.raises(ValidationError) as e:
        TypeAdapter(type_).validate_python(value)
    return {**e.value.errors()[0], "loc": ("body", "campo")}


def test_datetime_errors_say_what_is_expected():
    text = describe(error_of(datetime, "ontem"))
    assert text.startswith("campo: ") and "data e hora" in text and "valor inválido" not in text


def test_enum_errors_list_the_allowed_values():
    from app.models import Priority

    text = describe(error_of(Priority, "urgentissima"))
    assert "critica" in text and "media" in text and "rotina" in text


def test_http_errors_with_codes_outside_the_enum_do_not_crash():
    mini = FastAPI()
    install(mini)

    @mini.get("/x")
    def x():
        raise HTTPException(status_code=499, detail="cliente fechou")

    r = TestClient(mini).get("/x")
    assert r.status_code == 499 and r.json() == {"detail": "cliente fechou"}
