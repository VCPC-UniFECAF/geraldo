from abc import ABC, abstractmethod

from app.models import DeliveryStatus, Priority


class PriorityPolicy(ABC):  # STRATEGY: cada prioridade sabe sua posição na fila e como a entrega nasce
    @property
    @abstractmethod
    def priority(self) -> Priority: ...

    @property
    @abstractmethod
    def rank(self) -> int:
        """Menor número sai primeiro da fila."""

    @property
    @abstractmethod
    def initial_status(self) -> DeliveryStatus: ...

    @property
    def needs_approval(self) -> bool:
        """Exige a assinatura do farmacêutico antes de entrar na fila."""
        return self.initial_status == DeliveryStatus.PENDENTE_APROVACAO


class Critical(PriorityPolicy):
    priority = Priority.critica
    rank = 0
    initial_status = DeliveryStatus.PENDENTE_APROVACAO  # exige a assinatura do farmacêutico


class Standard(PriorityPolicy):
    priority = Priority.media
    rank = 1
    initial_status = DeliveryStatus.NA_FILA


class Routine(PriorityPolicy):
    priority = Priority.rotina
    rank = 2
    initial_status = DeliveryStatus.NA_FILA


_POLICIES = {policy.priority: policy for policy in (Critical(), Standard(), Routine())}


def policy_for(priority: Priority) -> PriorityPolicy:  # FACTORY: nova prioridade = classe nova + uma linha acima
    return _POLICIES[priority]
