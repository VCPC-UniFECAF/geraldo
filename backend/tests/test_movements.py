import pytest

from app.models import MovementType, Stock
from app.movements import ReservaCreator


def make_stock() -> Stock:
    return Stock(location_id="farmacia", item_id="dipirona-500mg", quantity=10, reserved=1)


def test_reserva_raises_reserved_and_returns_the_record():
    stock = make_stock()
    movement = ReservaCreator().register(stock, delivery_id=7, quantity=3)
    assert (stock.quantity, stock.reserved) == (10, 4)
    assert (movement.type, movement.item_id, movement.location_id, movement.quantity, movement.delivery_id) == (
        MovementType.RESERVA,
        "dipirona-500mg",
        "farmacia",
        3,
        7,
    )


@pytest.mark.parametrize("quantity", [0, -2])
def test_quantity_must_be_positive_and_stock_stays_untouched(quantity):
    stock = make_stock()
    with pytest.raises(ValueError):
        ReservaCreator().register(stock, delivery_id=1, quantity=quantity)
    assert (stock.quantity, stock.reserved) == (10, 1)
