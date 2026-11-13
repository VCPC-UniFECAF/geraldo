from datetime import datetime

import pytest
from sqlmodel import select

from app.clock import FixedClock, OffPeakWindow, get_clock
from app.commands.create_delivery import CreateDelivery
from app.commands.next_task import NextTask
from app.config import settings
from app.events import DeliveryChanged, Subject
from app.main import app
from app.models import Delivery, DeliveryStatus, Priority, User
from app.schemas import DeliveryCreate, DeliveryItemIn
from tests.conftest import SpyObserver


@pytest.mark.parametrize(
    "start, end, hour, expected",
    [(20, 6, 22, True), (20, 6, 3, True), (20, 6, 6, False), (20, 6, 14, False), (20, 6, 20, True), (9, 17, 12, True), (9, 17, 17, False), (0, 24, 13, True)],
)
def test_off_peak_window_handles_midnight_wraparound(start, end, hour, expected):
    assert OffPeakWindow(start, end).contains(datetime(2026, 11, 13, hour, 30)) is expected


def make(session, username: str, priority: Priority) -> int:
    user = session.exec(select(User).where(User.username == username)).one()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=1)], priority=priority)
    return CreateDelivery(session, user, payload).execute().id


def test_routine_is_skipped_at_peak_and_dispatched_off_peak(session):
    routine = make(session, "medico1", Priority.rotina)
    media = make(session, "medico1", Priority.media)
    window = OffPeakWindow(20, 6)
    peak, night = FixedClock(datetime(2026, 11, 13, 14, 0)), FixedClock(datetime(2026, 11, 13, 22, 0))

    assert NextTask(session, peak, window).execute().delivery.id == media
    assert NextTask(session, peak, window).execute() is None  # só sobrou a rotina
    assert session.get(Delivery, routine).status == DeliveryStatus.NA_FILA
    assert NextTask(session, night, window).execute().delivery.id == routine


def test_command_notifies_the_status_change(session):
    delivery_id = make(session, "medico1", Priority.media)
    spy, subject = SpyObserver(), Subject()
    subject.add_observer(spy)
    NextTask(session, FixedClock(datetime(2026, 11, 13, 22, 0)), OffPeakWindow(20, 6), events=subject, actor="robo").execute()
    assert spy.events == [DeliveryChanged(delivery_id, DeliveryStatus.NA_FILA, DeliveryStatus.EM_ROTA, "robo")]


def test_endpoint_uses_the_injected_clock_and_the_configured_window(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "off_peak_start", 20)
    monkeypatch.setattr(settings, "off_peak_end", 6)
    body = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": "rotina"}
    delivery_id = client.post("/deliveries", json=body, headers=auth("medico1")).json()["id"]

    app.dependency_overrides[get_clock] = lambda: FixedClock(datetime(2026, 11, 13, 14, 0))
    assert client.post("/robot/next-task", headers=auth("robo")).status_code == 204
    app.dependency_overrides[get_clock] = lambda: FixedClock(datetime(2026, 11, 13, 23, 0))
    task = client.post("/robot/next-task", headers=auth("robo"))
    app.dependency_overrides.pop(get_clock)

    assert task.status_code == 200 and task.json()["id"] == delivery_id and task.json()["status"] == "EM_ROTA"
