#!/usr/bin/env python3
"""Gera docs/contracts/examples/robot-telemetry.json e robot-events.json a partir do código do robô.

Os exemplos usam o próprio build_telemetry e o próprio Dispatcher, então não saem do que o robô realmente envia.
Os testes conferem que os arquivos estão em dia e seguem o OpenAPI.

Uso: python3 robot/scripts/contract_examples.py
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "robot/ros2_ws/src/geraldo_dispatcher"))

from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
from geraldo_dispatcher.ports import BackendPort, Navigator  # noqa: E402
from geraldo_dispatcher.states import State  # noqa: E402
from geraldo_dispatcher.telemetry import build_telemetry  # noqa: E402
from geraldo_dispatcher.waypoints import Pose  # noqa: E402

EXAMPLES = ROOT / "docs/contracts/examples"
NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
DELIVERY_ID = 7
POSES = {
    "base_robo": Pose(6.5, 26.5, math.radians(270)),
    "farmacia_balcao": Pose(7.0, 24.0, math.radians(270)),
    "cons1_entrega": Pose(14.5, 4.0, math.radians(270)),
}
TASK = {"id": DELIVERY_ID, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega", "priority": "media"}

# estado: (pose, bateria, entrega em curso, rota)
SNAPSHOTS = {
    State.IDLE: (Pose(6.5, 26.5, -1.5708), 100.0, None, []),
    State.CARREGANDO: (Pose(7.0, 24.0, -1.5708), 99.8, DELIVERY_ID, []),
    State.A_CAMINHO: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, [(14.2, 28.9), (20.0, 28.9), (29.0, 28.9)]),
    State.CHEGOU: (Pose(14.5, 4.0, -1.5708), 98.0, DELIVERY_ID, []),
    State.AGUARDANDO_RETIRADA: (Pose(14.5, 4.0, -1.5708), 97.9, DELIVERY_ID, []),
    State.VOLTANDO: (Pose(10.0, 28.9, 3.1416), 97.0, DELIVERY_ID, [(10.0, 28.9), (6.5, 26.5)]),
    State.PARADA_EMERGENCIA: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, []),
}
# cenário: (statuses da entrega que o backend devolve, a origem é inalcançável?)
SCENARIOS = {
    "entrega_concluida": (["ENTREGUE"], False),
    "falha_na_origem": (["ENTREGUE"], True),
    "entrega_cancelada": (["CANCELADA"], False),
    "recebimento_nao_confirmado": (["AGUARDANDO_RECEBIMENTO"], False),
}


class _Backend(BackendPort):
    def __init__(self, statuses) -> None:
        self._statuses, self.events = list(statuses), []

    def next_task(self):
        return dict(TASK)

    def send_event(self, delivery_id, event, reason=None):
        self.events.append({"delivery_id": delivery_id, "event": event, "reason": reason})
        return True

    def delivery_status(self, delivery_id):
        return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]


class _Navigator(Navigator):
    def __init__(self, fails_at) -> None:
        self._fails_at = fails_at

    def go_to(self, pose):
        return pose != self._fails_at


def telemetry_examples() -> dict[str, dict]:
    return {state.value: build_telemetry(state, pose, battery, delivery_id, route, [], NOW)
            for state, (pose, battery, delivery_id, route) in SNAPSHOTS.items()}


def event_examples() -> dict[str, list[dict]]:
    examples = {}
    for name, (statuses, origin_unreachable) in SCENARIOS.items():
        backend = _Backend(statuses)
        navigator = _Navigator(POSES["farmacia_balcao"] if origin_unreachable else None)
        Dispatcher(backend, POSES, navigator, sleep=lambda _: None, receipt_timeout=4.0, log=lambda *_: None).run_once()
        examples[name] = backend.events
    return examples


def main() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    for filename, data in (("robot-telemetry.json", telemetry_examples()), ("robot-events.json", event_examples())):
        (EXAMPLES / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"gerado: {EXAMPLES / filename}")


if __name__ == "__main__":
    main()
