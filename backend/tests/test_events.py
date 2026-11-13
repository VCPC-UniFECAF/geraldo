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


class Broken:
    def update(self, event) -> None:
        raise RuntimeError("observador quebrado")


def test_a_failing_observer_does_not_stop_the_others_nor_the_caller(caplog):
    subject, after = Subject(), Spy()
    subject.add_observer(Broken())
    subject.add_observer(after)
    subject.notify("x")  # não levanta
    assert after.events == ["x"]
    assert any("observador quebrado" in (r.exc_text or r.getMessage()) or r.exc_info for r in caplog.records)
    assert any(r.name == "geraldo.events" for r in caplog.records)


def test_observers_ignore_event_types_they_have_no_handler_for(caplog):
    caplog.set_level("INFO")
    AuditLog().update("evento desconhecido")
    LowStockAlert().update(EstopChanged(True, "admin"))
    assert not caplog.records


def test_low_stock_alert_keeps_only_the_latest_alerts():
    alert = LowStockAlert()
    for n in range(150):
        alert.update(StockChanged("farmacia", f"item{n}", quantity=0, reserved=0, minimum=5))
    assert len(alert.alerts) == 100 and "item149" in alert.alerts[-1] and "item50" in alert.alerts[0]


def test_audit_log_writes_the_failure_reason_on_one_clean_line(caplog):
    caplog.set_level("INFO", logger="geraldo.audit")
    reason = "tampa travada\nINFO fake: entrega 99 ENTREGUE\r" + "x" * 300
    AuditLog().update(DeliveryChanged(5, DeliveryStatus.EM_ROTA, DeliveryStatus.FALHOU, "robo", reason))
    message = caplog.records[0].getMessage()
    assert message.startswith("entrega 5: EM_ROTA -> FALHOU (por robo), motivo: tampa travada INFO fake")
    assert "\n" not in message and "\r" not in message and len(message) < 300
