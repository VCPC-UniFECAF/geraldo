import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.errors import install as install_error_handlers
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, estop, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("GERALDO_JWT_SECRET precisa ter pelo menos 32 caracteres. Gere um: python -c 'import secrets; print(secrets.token_hex(32))'")
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


def configure_logging() -> None:
    """A trilha de auditoria e os alertas de estoque saem no terminal do servidor (o uvicorn só configura o log dele)."""
    log = logging.getLogger("geraldo")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)


configure_logging()
events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(estop.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
