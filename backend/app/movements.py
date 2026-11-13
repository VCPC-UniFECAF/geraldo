from abc import ABC, abstractmethod

from app.models import Movement, MovementType, Stock


class MovementCreator(ABC):  # FACTORY METHOD + TEMPLATE METHOD: o único lugar que muda o saldo
    @property
    @abstractmethod
    def type(self) -> MovementType: ...

    @abstractmethod
    def apply(self, stock: Stock, quantity: int) -> None:
        """Efeito deste tipo de movimentação no saldo."""

    def register(self, stock: Stock, *, delivery_id: int | None, quantity: int) -> Movement:
        if quantity <= 0:
            raise ValueError("A quantidade da movimentação deve ser positiva.")
        self.apply(stock, quantity)
        return Movement(
            delivery_id=delivery_id,
            type=self.type,
            item_id=stock.item_id,
            location_id=stock.location_id,
            quantity=quantity,
        )


class ReservaCreator(MovementCreator):
    type = MovementType.RESERVA

    def apply(self, stock: Stock, quantity: int) -> None:
        stock.reserved += quantity


# Semana 2: BaixaCreator, CreditoCreator e EstornoCreator entram como classes novas, sem mexer nas existentes (OCP).
