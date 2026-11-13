import logging
import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from app.models import DeliveryStatus


@dataclass(frozen=True)
class DeliveryChanged:
    """Uma entrega nasceu (old_status None) ou mudou de status."""

    delivery_id: int
    old_status: DeliveryStatus | None
    new_status: DeliveryStatus
    actor: str
    reason: str | None = None  # só no FAILED do robô: por que a entrega falhou


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
        """Um observador que falha não derruba os outros nem o request (a mudança já foi gravada): o erro vai para o log."""
        for observer in list(self._observers):
            try:
                observer.update(event)
            except Exception:
                logging.getLogger("geraldo.events").exception("O observador %s falhou ao tratar %s.", type(observer).__name__, type(event).__name__)


class _TypedObserver:
    """Base dos observadores: despacha pelo tipo do evento, numa tabela (sem if/elif por tipo). Tipo sem linha é ignorado."""

    def __init__(self) -> None:
        self._handlers: dict[type, Callable] = {}

    def update(self, event) -> None:
        handler = self._handlers.get(type(event))
        if handler:
            handler(event)


class AuditLog(_TypedObserver):  # OBSERVER: trilha de auditoria no log do servidor
    def __init__(self, logger: logging.Logger | None = None) -> None:
        super().__init__()
        self._logger = logger or logging.getLogger("geraldo.audit")
        self._handlers = {DeliveryChanged: self._on_delivery, EstopChanged: self._on_estop}

    def _on_delivery(self, event: DeliveryChanged) -> None:
        old = event.old_status.value if event.old_status else "nova"
        reason = f", motivo: {self._one_line(event.reason)}" if event.reason else ""
        self._logger.info("entrega %s: %s -> %s (por %s)%s", event.delivery_id, old, event.new_status.value, event.actor, reason)

    def _on_estop(self, event: EstopChanged) -> None:
        self._logger.warning("parada de emergência %s por %s", "LIGADA" if event.active else "desligada", event.actor)

    @staticmethod
    def _one_line(text: str) -> str:
        """Texto livre vindo do robô: sem quebra de linha (não forja outra linha de log) e no máximo 200 caracteres."""
        return re.sub(r"[\x00-\x1f\x7f]+", " ", text)[:200]


class LowStockAlert(_TypedObserver):  # OBSERVER: avisa quando o saldo fica abaixo do mínimo
    def __init__(self, logger: logging.Logger | None = None, keep: int = 100) -> None:
        super().__init__()
        self._logger = logger or logging.getLogger("geraldo.stock")
        self.alerts: deque[str] = deque(maxlen=keep)  # só os mais recentes: não cresce para sempre
        self._handlers = {StockChanged: self._on_stock}

    def _on_stock(self, event: StockChanged) -> None:
        if event.quantity < event.minimum:
            message = f"Estoque baixo: {event.item_id} em {event.location_id} tem {event.quantity} (mínimo {event.minimum}). Reponha."
            self.alerts.append(message)
            self._logger.warning(message)


# Assinante único do processo; main.py liga AuditLog e LowStockAlert nele. Os testes injetam um Subject próprio.
events = Subject()


def get_events() -> Subject:
    return events
