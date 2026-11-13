import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402
from tools.mock_robot import MockRobot  # noqa: E402

from app.main import app  # noqa: E402
from app.telemetry import TelemetryHub, get_hub  # noqa: E402
from tests.conftest import PASSWORD  # noqa: E402

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 3}], "priority": "media"}
POLL = 0.5


@pytest.fixture(autouse=True)
def fresh_hub(client):
    hub = TelemetryHub()
    app.dependency_overrides[get_hub] = lambda: hub
    yield
    app.dependency_overrides.pop(get_hub, None)


def test_mock_robot_delivers_end_to_end_against_the_real_api(client, auth):
    delivery_id = client.post("/deliveries", json=BODY, headers=auth("medico1")).json()["id"]
    robot = MockRobot(client, "robo", PASSWORD)  # o TestClient é um httpx.Client
    robot.login()
    confirmed = []

    def sleep(seconds: float) -> None:
        if seconds == POLL and not confirmed:  # o robô está esperando: o solicitante confirma o recebimento
            r = client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
            assert r.status_code == 200, r.text
            confirmed.append(True)

    task = robot.run_once(report=True, sleep=sleep, poll_seconds=POLL)

    assert task["id"] == delivery_id and task["origin_waypoint"] == "farmacia_balcao" and task["dest_waypoint"] == "cons1_entrega"
    assert confirmed == [True]
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"] == "ENTREGUE"
    stock = {s["location_id"]: s for s in client.get("/stock", headers=auth("medico1")).json() if s["item_id"] == "dipirona-500mg"}
    assert (stock["farmacia"]["quantity"], stock["farmacia"]["reserved"], stock["consultorio1"]["quantity"]) == (417, 0, 3)
    assert client.get("/telemetry", headers=auth("medico1")).json()["robot_state"] == "IDLE"
    assert robot.run_once(sleep=lambda s: None) is None  # fila vazia
