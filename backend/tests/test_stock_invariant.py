import time
from datetime import datetime
from threading import Barrier, Thread

import pytest
from sqlmodel import Session, select

from app.clock import FixedClock, OffPeakWindow
from app.commands.create_delivery import CreateDelivery
from app.commands.errors import InsufficientStock
from app.commands.next_task import NextTask
from app.db import create_db, make_engine
from app.models import Delivery, Priority, Stock, User
from app.movements import BaixaCreator, ReservaCreator
from app.priority import policy_for
from app.schemas import DeliveryCreate, DeliveryItemIn
from app.seed import seed
from tests.conftest import FIXTURES


def stock(quantity=10, reserved=0) -> Stock:
    return Stock(location_id="farmacia", item_id="dipirona-500mg", quantity=quantity, reserved=reserved)


def test_reserva_refuses_more_than_the_available():
    s = stock(quantity=10, reserved=8)
    with pytest.raises(ValueError, match="disponível"):
        ReservaCreator().register(s, delivery_id=1, quantity=3)
    assert (s.quantity, s.reserved) == (10, 8)


def test_reserva_accepts_exactly_the_available():
    s = stock(quantity=10, reserved=8)
    ReservaCreator().register(s, delivery_id=1, quantity=2)
    assert s.reserved == 10


def test_baixa_never_takes_the_balance_below_zero():
    s = stock(quantity=2, reserved=5)  # estado corrompido: reservado maior que o saldo
    with pytest.raises(ValueError, match="saldo"):
        BaixaCreator().register(s, delivery_id=1, quantity=3)
    assert (s.quantity, s.reserved) == (2, 5)


class SlowReserva(ReservaCreator):
    """Alarga a janela entre ler o saldo e gravar: sem trava, todas as threads gravam por cima umas das outras."""

    def apply(self, stock: Stock, quantity: int) -> None:
        time.sleep(0.05)
        super().apply(stock, quantity)


@pytest.fixture
def file_engine(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path}/c.db")
    create_db(eng)
    with Session(eng) as s:
        seed(s, FIXTURES)
    return eng


def run_threads(n, target):
    barrier, results = Barrier(n), []

    def worker():
        barrier.wait()
        results.append(target())

    threads = [Thread(target=worker) for _ in range(n)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return results


def test_concurrent_requests_never_over_reserve(file_engine):
    def order():
        with Session(file_engine) as s:
            user = s.exec(select(User).where(User.username == "medico1")).one()
            payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=150)], priority=Priority.media)
            try:
                CreateDelivery(s, user, payload, reserva=SlowReserva()).execute()
                return "ok"
            except InsufficientStock:
                return "recusado"

    results = run_threads(6, order)  # saldo 420: cabem 2 pedidos de 150 (300), o terceiro passaria de 420 com 450

    assert results.count("ok") == 2 and results.count("recusado") == 4
    with Session(file_engine) as s:
        row = s.get(Stock, ("farmacia", "dipirona-500mg"))
        assert (row.quantity, row.reserved) == (420, 300)


def test_two_robots_never_get_the_same_delivery(file_engine):
    with Session(file_engine) as s:
        user = s.exec(select(User).where(User.username == "medico1")).one()
        payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=1)], priority=Priority.media)
        CreateDelivery(s, user, payload).execute()

    def slow_policy(priority):
        time.sleep(0.05)
        return policy_for(priority)

    def ask():
        with Session(file_engine) as s:
            return NextTask(s, FixedClock(datetime(2026, 11, 13, 22, 0)), OffPeakWindow(20, 6), policy_for=slow_policy).execute()

    got = [r for r in run_threads(4, ask) if r is not None]
    assert len(got) == 1
