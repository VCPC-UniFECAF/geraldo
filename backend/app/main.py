from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.routers import auth
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
