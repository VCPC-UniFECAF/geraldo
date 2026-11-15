import asyncio

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .gazebo_gui import GuiError
from .ports import RosPort
from .state import BridgeState

HOST = "127.0.0.1"  # só a própria máquina: a ponte não tem login
PORT = 8765
ALLOWED_HOSTS = ("127.0.0.1", "localhost")  # barra DNS rebinding
ALLOWED_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")  # o app (e o `npm run dev`) servem o web aqui
WS_INTERVAL_S = 0.1  # 10 mensagens por segundo


class EstopBody(BaseModel):
    active: bool


def create_app(state: BridgeState, port: RosPort, gui, interval_s: float = WS_INTERVAL_S) -> FastAPI:
    app = FastAPI(title="G.E.R.A.L.D.O. ponte ROS", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def reject_foreign_origins(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"detail": "Origem não permitida. Abra a visão 2D pelo aplicativo do G.E.R.A.L.D.O."}, status_code=403)
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware, allow_origins=list(ALLOWED_ORIGINS), allow_methods=["GET", "POST"], allow_headers=["content-type"]
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS))

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/snapshot")
    def snapshot() -> dict:
        return state.snapshot()

    @app.post("/estop", status_code=204, response_class=Response)
    def estop(body: EstopBody) -> None:
        port.publish_estop(body.active)
        state.update_estop(body.active)

    @app.post("/gazebo/gui", status_code=202)
    def open_gazebo() -> dict:
        try:
            pid, already_running = gui.open()
        except GuiError as err:
            raise HTTPException(status_code=500, detail=str(err)) from err
        return {"pid": pid, "already_running": already_running}

    @app.websocket("/ws/sim")
    async def sim_stream(ws: WebSocket) -> None:
        origin = ws.headers.get("origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            while True:
                await ws.send_json(state.snapshot())
                await asyncio.sleep(interval_s)
        except WebSocketDisconnect:
            pass

    return app
