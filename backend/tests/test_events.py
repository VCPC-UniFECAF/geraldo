from sqlmodel import select

from app.commands.create_delivery import CreateDelivery
from app.events import AuditLog, DeliveryChanged, EstopChanged, LowStockAlert, StockChanged, Subject
from app.models import DeliveryStatus, Priority, User
from app.schemas import DeliveryCreate, DeliveryItemIn


class Spy:
    def __init__(self) -> None:
        self.events = []

    def update(self, event) -> None:
        self.events.append(event)


def test_subject_notifies_every_observer_and_stops_after_remove():
    subject, a, b = Subject(), Spy(), Spy()
    subject.add_observer(a)
    subject.add_observer(b)
    subject.notify("x")
    subject.remove_observer(b)
    subject.notify("y")
    assert a.events == ["x", "y"] and b.events == ["x"]


def test_low_stock_alert_only_fires_below_the_minimum():
    alert = LowStockAlert()
    alert.update(StockChanged("banco_sangue", "bolsa-sangue-o-neg", quantity=6, reserved=0, minimum=10))
    alert.update(StockChanged("farmacia", "dipirona-500mg", quantity=420, reserved=0, minimum=100))
    alert.update(StockChanged("farmacia", "luva-procedimento", quantity=40, reserved=0, minimum=40))
    assert len(alert.alerts) == 1
    assert "bolsa-sangue-o-neg" in alert.alerts[0] and "Reponha" in alert.alerts[0]


def test_audit_log_writes_delivery_and_estop_events(caplog):
    caplog.set_level("INFO", logger="geraldo.audit")
    log = AuditLog()
    log.update(DeliveryChanged(7, None, DeliveryStatus.NA_FILA, "medico1"))
    log.update(EstopChanged(True, "admin"))
    log.update(StockChanged("farmacia", "dipirona-500mg", 1, 0, 0))  # ignorado
    assert [r.getMessage() for r in caplog.records] == [
        "entrega 7: nova -> NA_FILA (por medico1)",
        "parada de emergência LIGADA por admin",
    ]


def test_create_delivery_notifies_the_delivery_and_the_reserved_stock(session):
    user = session.exec(select(User).where(User.username == "medico1")).one()
    spy, subject = Spy(), Subject()
    subject.add_observer(spy)
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=2)], priority=Priority.media)

    delivery = CreateDelivery(session, user, payload, events=subject).execute()

    assert spy.events == [
        DeliveryChanged(delivery.id, None, DeliveryStatus.NA_FILA, "medico1"),
        StockChanged("farmacia", "dipirona-500mg", quantity=420, reserved=2, minimum=100),
    ]
