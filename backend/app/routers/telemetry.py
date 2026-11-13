import asyncio

from fastapi import APIRouter, Depends, WebSocket
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user, user_from_token
from app.models import User
from app.schemas import TelemetryOut
from app.telemetry import TelemetryHub, get_hub

router = APIRouter()


@router.get("/telemetry", response_model=TelemetryOut)
def last_telemetry(_: User = Depends(get_current_user), hub: TelemetryHub = Depends(get_hub)):
    return hub.latest()


class _Subscriber:  # OBSERVER: assinante do hub para um WebSocket
    """O POST roda em outra thread, então a entrega passa pelo loop do socket."""

    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.queue: asyncio.Queue = asyncio.Queue()

    def update(self, telemetry: TelemetryOut) -> None:
        self._loop.call_soon_threadsafe(self.queue.put_nowait, telemetry.model_dump(mode="json"))


async def _wait_disconnect(ws: WebSocket) -> None:
    while (await ws.receive())["type"] != "websocket.disconnect":
        pass


def _token_of(ws: WebSocket) -> str | None:
    """O navegador não envia cabeçalho no WebSocket: o token vem em ?token=...; clientes de linha de comando usam Authorization."""
    header = ws.headers.get("authorization", "")
    return ws.query_params.get("token") or (header[7:] if header.lower().startswith("bearer ") else None)


@router.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket, hub: TelemetryHub = Depends(get_hub), session: Session = Depends(get_session)):
    token = _token_of(ws)
    user = user_from_token(token, session) if token else None
    if user is None:
        await ws.close(code=1008, reason="Faça login: informe o token em ?token=")
        return
    await ws.accept()
    subscriber = _Subscriber()
    hub.add_observer(subscriber)
    gone = asyncio.create_task(_wait_disconnect(ws))
    try:
        await ws.send_json(hub.latest().model_dump(mode="json"))  # quem entra já recebe o último estado
        while not gone.done():
            getter = asyncio.create_task(subscriber.queue.get())
            await asyncio.wait({getter, gone}, return_when=asyncio.FIRST_COMPLETED)
            if getter.done():
                await ws.send_json(getter.result())
            else:
                getter.cancel()
    finally:
        hub.remove_observer(subscriber)
        gone.cancel()
