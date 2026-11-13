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


def _must_have_reserved(stock: Stock, quantity: int) -> None:
    if stock.reserved < quantity:
        raise ValueError(
            f"Só há {stock.reserved} reservado de {stock.item_id} em {stock.location_id}; não dá para liberar {quantity}. "
            "Confira as movimentações da entrega."
        )


class ReservaCreator(MovementCreator):
    """Separa a quantidade para uma entrega: o saldo continua, o disponível diminui."""

    type = MovementType.RESERVA

    def apply(self, stock: Stock, quantity: int) -> None:
        available = stock.quantity - stock.reserved
        if quantity > available:
            raise ValueError(
                f"Só há {available} disponível de {stock.item_id} em {stock.location_id}; não dá para reservar {quantity}. Reduza a quantidade."
            )
        stock.reserved += quantity


class BaixaCreator(MovementCreator):
    """A mercadoria saiu da origem: consome a reserva e o saldo."""

    type = MovementType.BAIXA

    def apply(self, stock: Stock, quantity: int) -> None:
        _must_have_reserved(stock, quantity)
        if stock.quantity < quantity:
            raise ValueError(
                f"O saldo de {stock.item_id} em {stock.location_id} é {stock.quantity}; não dá para dar baixa de {quantity}. Confira o estoque."
            )
        stock.reserved -= quantity
        stock.quantity -= quantity


class CreditoCreator(MovementCreator):
    """A mercadoria chegou ao destino: soma ao saldo."""

    type = MovementType.CREDITO

    def apply(self, stock: Stock, quantity: int) -> None:
        stock.quantity += quantity


class EstornoCreator(MovementCreator):
    """Desfaz a reserva (entrega cancelada ou que falhou): o saldo não muda."""

    type = MovementType.ESTORNO

    def apply(self, stock: Stock, quantity: int) -> None:
        _must_have_reserved(stock, quantity)
        stock.reserved -= quantity


_CREATORS = {creator.type: creator for creator in (ReservaCreator(), BaixaCreator(), CreditoCreator(), EstornoCreator())}


def creator_for(type: MovementType) -> MovementCreator:  # FACTORY: tipo novo = classe nova + uma linha acima
    return _CREATORS[type]
