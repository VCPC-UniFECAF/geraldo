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
    SQLModel.metadata.create_all(eng or engine)


def get_session():
    with Session(engine) as session:
        yield session
