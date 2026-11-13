import pytest

from app.models import MovementType, Stock
from app.movements import BaixaCreator, CreditoCreator, EstornoCreator, ReservaCreator, creator_for


def make_stock(quantity: int = 10, reserved: int = 1) -> Stock:
    return Stock(location_id="farmacia", item_id="dipirona-500mg", quantity=quantity, reserved=reserved)


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


def test_baixa_consumes_the_reservation_and_the_balance():
    stock = make_stock(quantity=10, reserved=4)
    movement = BaixaCreator().register(stock, delivery_id=7, quantity=3)
    assert (stock.quantity, stock.reserved) == (7, 1)
    assert movement.type == MovementType.BAIXA and movement.quantity == 3


def test_credito_adds_to_the_balance_only():
    stock = make_stock(quantity=2, reserved=0)
    movement = CreditoCreator().register(stock, delivery_id=7, quantity=3)
    assert (stock.quantity, stock.reserved) == (5, 0)
    assert movement.type == MovementType.CREDITO


def test_estorno_releases_the_reservation_and_keeps_the_balance():
    stock = make_stock(quantity=10, reserved=4)
    movement = EstornoCreator().register(stock, delivery_id=7, quantity=4)
    assert (stock.quantity, stock.reserved) == (10, 0)
    assert movement.type == MovementType.ESTORNO


@pytest.mark.parametrize("creator", [BaixaCreator(), EstornoCreator()])
def test_cannot_release_more_than_what_is_reserved(creator):
    stock = make_stock(quantity=10, reserved=1)
    with pytest.raises(ValueError, match="reservado"):
        creator.register(stock, delivery_id=7, quantity=2)
    assert (stock.quantity, stock.reserved) == (10, 1)


@pytest.mark.parametrize("creator", [ReservaCreator(), BaixaCreator(), CreditoCreator(), EstornoCreator()])
@pytest.mark.parametrize("quantity", [0, -2])
def test_quantity_must_be_positive_and_stock_stays_untouched(creator, quantity):
    stock = make_stock()
    with pytest.raises(ValueError):
        creator.register(stock, delivery_id=1, quantity=quantity)
    assert (stock.quantity, stock.reserved) == (10, 1)


def test_creator_for_returns_one_creator_per_type():
    for type in MovementType:
        assert creator_for(type).type == type
