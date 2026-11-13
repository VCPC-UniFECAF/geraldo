from sqlmodel import select

from app.models import Item, Location, Role, Stock, User
from app.seed import seed
from tests.conftest import FIXTURES, PASSWORD


def test_seed_creates_locations_items_stock_and_users(session):
    assert session.get(Location, "farmacia").waypoint == "farmacia_balcao"
    assert session.get(Location, "recepcao").waypoint is None
    assert session.get(Item, "dipirona-500mg").name == "Dipirona 500 mg"
    stock = session.get(Stock, ("farmacia", "dipirona-500mg"))
    assert (stock.quantity, stock.reserved, stock.minimum) == (420, 0, 100)
    medico = session.exec(select(User).where(User.username == "medico1")).one()
    assert medico.role == Role.medico and medico.local_id == "consultorio1"
    assert session.exec(select(User).where(User.username == "robo")).one().role == Role.robo


def test_passwords_are_stored_hashed(session):
    user = session.exec(select(User).where(User.username == "medico1")).one()
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("pbkdf2_sha256$")


def test_seed_is_idempotent_and_never_overwrites_stock(session):
    stock = session.get(Stock, ("farmacia", "dipirona-500mg"))
    stock.quantity = 7
    session.add(stock)
    session.commit()
    seed(session, FIXTURES)
    assert session.get(Stock, ("farmacia", "dipirona-500mg")).quantity == 7
    assert len(session.exec(select(User)).all()) == 6
    assert len(session.exec(select(Location)).all()) == 6
