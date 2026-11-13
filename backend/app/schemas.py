from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DeliveryStatus, MovementType, Priority, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: Role
    local_id: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    has_stock: bool
    waypoint: str | None = None


class StockOut(BaseModel):
    location_id: str
    item_id: str
    item_name: str
    quantity: int
    reserved: int
    minimum: int


class DeliveryItemIn(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class DeliveryCreate(BaseModel):
    origin_id: str
    dest_id: str | None = None
    items: list[DeliveryItemIn] = Field(min_length=1)
    priority: Priority


class DeliveryOut(BaseModel):
    id: int
    origin_id: str
    dest_id: str
    items: list[DeliveryItemIn]
    priority: Priority
    status: DeliveryStatus
    requested_by: int
    created_at: datetime


class RobotTaskOut(DeliveryOut):
    origin_waypoint: str
    dest_waypoint: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_id: int | None
    type: MovementType
    item_id: str
    location_id: str
    quantity: int
    created_at: datetime


class RobotEventType(str, Enum):
    LOADED = "LOADED"
    ARRIVED = "ARRIVED"
    UNLOCKED = "UNLOCKED"
    FAILED = "FAILED"


class RobotEventIn(BaseModel):
    delivery_id: int
    event: RobotEventType
    reason: str | None = Field(default=None, max_length=200)


Meters = Annotated[float, Field(allow_inf_nan=False, ge=-1000, le=1000)]  # o hospital cabe folgado em 2 km


class RobotState(str, Enum):
    IDLE = "IDLE"
    CARREGANDO = "CARREGANDO"
    A_CAMINHO = "A_CAMINHO"
    CHEGOU = "CHEGOU"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"
    VOLTANDO = "VOLTANDO"
    PARADA_EMERGENCIA = "PARADA_EMERGENCIA"


class PoseIn(BaseModel):
    x: Meters
    y: Meters
    yaw: Annotated[float, Field(allow_inf_nan=False, ge=-10, le=10)]  # radianos


class PointIn(BaseModel):
    x: Meters
    y: Meters


class ObstacleIn(BaseModel):
    x: Meters
    y: Meters
    radius: Annotated[float, Field(allow_inf_nan=False, ge=0, le=50)]


class TelemetryIn(BaseModel):
    """Corpo do POST /robot/telemetry. O updated_at do robô é aceito e ignorado: vale a hora de recebimento."""

    robot_state: RobotState
    pose: PoseIn
    battery: Annotated[float, Field(allow_inf_nan=False, ge=0, le=100)]
    delivery_id: int | None = None
    route: list[PointIn] = Field(default_factory=list, max_length=50)
    obstacles: list[ObstacleIn] = Field(default_factory=list, max_length=20)
    updated_at: datetime | None = None


class TelemetryOut(TelemetryIn):
    updated_at: datetime
