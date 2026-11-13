import json
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.models import Item, Location, Role, Stock, User
from app.security import hash_password

SEEDS = Path(__file__).resolve().parent.parent / "seeds"

# (username, papel, local padrão). Todos usam GERALDO_DEMO_PASSWORD; só para demonstração.
DEMO_USERS = [
    ("medico1", Role.medico, "consultorio1"),
    ("medico2", Role.medico, "consultorio2"),
    ("enfermeiro1", Role.enfermeiro, "enfermaria214"),
    ("farmaceutico1", Role.farmaceutico, "farmacia"),
    ("admin", Role.admin, None),
    ("robo", Role.robo, None),
]


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed(session: Session, seeds_dir: Path = SEEDS) -> None:
    """Insere o que falta; nunca sobrescreve estoque nem usuários existentes."""
    for loc in _load(seeds_dir / "locais.json"):
        if session.get(Location, loc["id"]) is None:
            session.add(Location(**loc))
    for item in _load(seeds_dir / "itens.json"):
        if session.get(Item, item["id"]) is None:
            session.add(Item(**item))
    session.commit()
    for st in _load(seeds_dir / "estoque.json"):
        if session.get(Stock, (st["location_id"], st["item_id"])) is None:
            session.add(Stock(**st))
    for username, role, local_id in DEMO_USERS:
        if session.exec(select(User).where(User.username == username)).first() is None:
            session.add(User(username=username, password_hash=hash_password(settings.demo_password), role=role, local_id=local_id))
    session.commit()
