from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class Role(str, Enum):
    medico = "medico"
    enfermeiro = "enfermeiro"
    farmaceutico = "farmaceutico"
    admin = "admin"
    robo = "robo"


class Priority(str, Enum):
    critica = "critica"
    media = "media"
    rotina = "rotina"


class DeliveryStatus(str, Enum):
    PENDENTE_APROVACAO = "PENDENTE_APROVACAO"
    NA_FILA = "NA_FILA"
    EM_ROTA = "EM_ROTA"
    AGUARDANDO_RECEBIMENTO = "AGUARDANDO_RECEBIMENTO"
    ENTREGUE = "ENTREGUE"
    CANCELADA = "CANCELADA"
    FALHOU = "FALHOU"


class MovementType(str, Enum):
    RESERVA = "RESERVA"
    BAIXA = "BAIXA"
    CREDITO = "CREDITO"
    ESTORNO = "ESTORNO"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: Role
    local_id: str | None = Field(default=None, foreign_key="location.id")


class Location(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    kind: str
    has_stock: bool = False
    waypoint: str | None = None


class Item(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    unit: str


class Stock(SQLModel, table=True):
    location_id: str = Field(foreign_key="location.id", primary_key=True)
    item_id: str = Field(foreign_key="item.id", primary_key=True)
    quantity: int = 0
    reserved: int = 0
    minimum: int = 0


class Delivery(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    origin_id: str = Field(foreign_key="location.id")
    dest_id: str = Field(foreign_key="location.id")
    priority: Priority
    status: DeliveryStatus
    requested_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)


class DeliveryItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    delivery_id: int = Field(foreign_key="delivery.id", index=True)
    item_id: str = Field(foreign_key="item.id")
    quantity: int


class Movement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    delivery_id: int | None = Field(default=None, foreign_key="delivery.id")
    type: MovementType
    item_id: str = Field(foreign_key="item.id")
    location_id: str = Field(foreign_key="location.id")
    quantity: int
    created_at: datetime = Field(default_factory=utcnow)
