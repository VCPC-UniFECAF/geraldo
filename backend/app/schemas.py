from datetime import datetime
from typing import Literal

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
