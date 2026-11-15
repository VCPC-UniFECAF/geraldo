from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def make_engine(url: str):
    kwargs: dict = {"connect_args": {"check_same_thread": False}}
    if url in ("sqlite://", "sqlite:///:memory:"):
        kwargs["poolclass"] = StaticPool  # uma única conexão: o banco em memória vive entre as threads do TestClient
    return create_engine(url, **kwargs)


engine = make_engine(settings.database_url)


def create_db(eng=None) -> None:
    eng = eng or engine
    SQLModel.metadata.create_all(eng)
    # Sem migrações: um banco criado antes da recusa não tem a coluna e daria erro em toda consulta de entrega.
    if "cancel_reason" not in {c["name"] for c in inspect(eng).get_columns("delivery")}:
        with eng.begin() as conn:
            conn.execute(text("ALTER TABLE delivery ADD COLUMN cancel_reason VARCHAR(200)"))


def get_session():
    with Session(engine) as session:
        yield session
