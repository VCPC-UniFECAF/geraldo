from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
