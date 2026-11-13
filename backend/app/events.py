import logging
from dataclasses import dataclass

from app.models import DeliveryStatus


@dataclass(frozen=True)
class DeliveryChanged:
    """Uma entrega nasceu (old_status None) ou mudou de status."""

    delivery_id: int
    old_status: DeliveryStatus | None
    new_status: DeliveryStatus
    actor: str


@dataclass(frozen=True)
class StockChanged:
    """O saldo de um item em um local mudou (por causa de uma movimentação)."""

    location_id: str
    item_id: str
    quantity: int
    reserved: int
    minimum: int


@dataclass(frozen=True)
class EstopChanged:
    """O painel ligou ou desligou a parada de emergência."""

    active: bool
    actor: str


class Subject:  # OBSERVER (mesmos nomes da disciplina)
    def __init__(self) -> None:
        self._observers: list = []

    def add_observer(self, observer) -> None:
        self._observers.append(observer)

    def remove_observer(self, observer) -> None:
        self._observers.remove(observer)

    def notify(self, event) -> None:
        for observer in list(self._observers):
            observer.update(event)


class AuditLog:  # OBSERVER: trilha de auditoria no log do servidor
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("geraldo.audit")

    def update(self, event) -> None:
        if isinstance(event, DeliveryChanged):
            old = event.old_status.value if event.old_status else "nova"
            self._logger.info("entrega %s: %s -> %s (por %s)", event.delivery_id, old, event.new_status.value, event.actor)
        elif isinstance(event, EstopChanged):
            self._logger.warning("parada de emergência %s por %s", "LIGADA" if event.active else "desligada", event.actor)


class LowStockAlert:  # OBSERVER: avisa quando o saldo fica abaixo do mínimo
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("geraldo.stock")
        self.alerts: list[str] = []

    def update(self, event) -> None:
        if isinstance(event, StockChanged) and event.quantity < event.minimum:
            message = f"Estoque baixo: {event.item_id} em {event.location_id} tem {event.quantity} (mínimo {event.minimum}). Reponha."
            self.alerts.append(message)
            self._logger.warning(message)


# Assinante único do processo; main.py liga AuditLog e LowStockAlert nele. Os testes injetam um Subject próprio.
events = Subject()


def get_events() -> Subject:
    return events
