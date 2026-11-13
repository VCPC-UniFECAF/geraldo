#!/usr/bin/env python3
"""Robô de mentira: faz o papel do geraldo_dispatcher contra o backend, sem Gazebo nem ROS.

Segue a sequência de docs/contracts/robot-protocol.md (seção 2):
next-task -> LOADED -> ARRIVED -> espera o solicitante confirmar (ENTREGUE) -> UNLOCKED -> volta à base.

Uso (o backend precisa estar de pé, e a senha é a do usuário "robo"):
  GERALDO_ROBOT_PASSWORD=... python tools/mock_robot.py --api http://127.0.0.1:8000 --travel 5 --report
Renova o login sozinho (uma vez) se o backend responder 401. Não faz as 3 tentativas do dispatcher real
nem lê GET /robot/estop. Sem --report ele só pega a próxima tarefa e espera o tempo do trajeto (não manda eventos nem telemetria).
"""
import argparse
import os
import time

import httpx

BASE_POSE = (6.5, 26.5)  # valores de mentira: o robô "anda" 10 m em linha reta e volta
TRAVEL_METERS = 10.0


class MockRobot:
    def __init__(self, client: httpx.Client, username: str = "robo", password: str = "") -> None:
        self.client = client
        self.username = username
        self.password = password
        self._battery = 100.0

    def login(self) -> None:
        r = self.client.post("/auth/login", json={"username": self.username, "password": self.password})
        if r.status_code != 200:
            raise RuntimeError(f"Login do robô falhou ({r.status_code}): {r.text}")
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Token vencido ou backend reiniciado dá 401: login de novo e repete a chamada uma vez (robot-protocol.md, seção 6)."""
        response = self.client.request(method, url, **kwargs)
        if response.status_code == 401:
            self.login()
            response = self.client.request(method, url, **kwargs)
        return response

    def next_task(self) -> dict | None:
        r = self._send("POST", "/robot/next-task")
        if r.status_code == 204:
            return None
        r.raise_for_status()
        return r.json()

    def report(self, delivery_id: int, event: str, reason: str | None = None) -> dict | None:
        """Manda o evento. O 409 (ex.: FAILED de uma entrega já cancelada) só é registrado, como faz o dispatcher."""
        r = self._send("POST", "/robot/events", json={"delivery_id": delivery_id, "event": event, "reason": reason})
        if r.status_code == 409:
            print(f"evento {event} recusado (409): {r.json().get('detail')}")
            return None
        r.raise_for_status()
        return r.json()

    def send_telemetry(self, state: str, delivery_id: int | None = None, progress: float = 0.0) -> None:
        self._battery = max(0.0, self._battery - 0.2)
        body = {
            "robot_state": state,
            "pose": {"x": BASE_POSE[0] + TRAVEL_METERS * progress, "y": BASE_POSE[1], "yaw": 0.0},
            "battery": round(self._battery, 1),
            "delivery_id": delivery_id,
            "route": [],
            "obstacles": [],
        }
        self._send("POST", "/robot/telemetry", json=body).raise_for_status()

    def delivery_status(self, delivery_id: int) -> str:
        r = self._send("GET", f"/deliveries/{delivery_id}")
        r.raise_for_status()
        return r.json()["status"]

    def wait_for_receipt(self, delivery_id: int, poll_seconds: float, timeout_seconds: float, sleep=time.sleep) -> str:
        """Espera o status virar ENTREGUE. Devolve ENTREGUE, CANCELADA, FALHOU ou TIMEOUT."""
        waited = 0.0
        while True:
            try:
                status = self.delivery_status(delivery_id)
            except httpx.HTTPError:
                status = "AGUARDANDO_RECEBIMENTO"  # consulta que falha conta como "ainda não"
            if status in ("ENTREGUE", "CANCELADA", "FALHOU"):
                return status
            if waited >= timeout_seconds:
                return "TIMEOUT"
            sleep(poll_seconds)
            waited += poll_seconds

    def run_once(
        self,
        travel_seconds: float = 0.0,
        report: bool = False,
        sleep=time.sleep,
        poll_seconds: float = 2.0,
        receipt_timeout: float = 300.0,
    ) -> dict | None:
        task = self.next_task()
        if task is None:
            return None
        print(f"entrega {task['id']}: {task['origin_waypoint']} -> {task['dest_waypoint']}")
        if not report:
            sleep(travel_seconds)
            return task
        delivery_id = task["id"]
        self.send_telemetry("A_CAMINHO", delivery_id, 0.0)
        sleep(travel_seconds)
        self.send_telemetry("CARREGANDO", delivery_id, 0.0)
        self.report(delivery_id, "LOADED")
        self.send_telemetry("A_CAMINHO", delivery_id, 0.5)
        sleep(travel_seconds)
        self.send_telemetry("CHEGOU", delivery_id, 1.0)
        self.report(delivery_id, "ARRIVED")
        self.send_telemetry("AGUARDANDO_RETIRADA", delivery_id, 1.0)
        outcome = self.wait_for_receipt(delivery_id, poll_seconds, receipt_timeout, sleep)
        if outcome == "ENTREGUE":
            self.report(delivery_id, "UNLOCKED")  # a tampa só abre depois do ENTREGUE
        else:
            reason = {"CANCELADA": "entrega cancelada", "FALHOU": "entrega falhou"}.get(outcome, "recebimento não confirmado a tempo")
            self.report(delivery_id, "FAILED", reason)
        self.send_telemetry("VOLTANDO", None, 0.5)
        sleep(travel_seconds)
        self.send_telemetry("IDLE", None, 0.0)
        return task


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--user", default="robo")
    ap.add_argument("--travel", type=float, default=5.0, help="segundos de cada trecho do trajeto")
    ap.add_argument("--poll", type=float, default=2.0, help="segundos entre as consultas do status, esperando o recebimento")
    ap.add_argument("--timeout", type=float, default=300.0, help="segundos esperando o recebimento antes de falhar a entrega")
    ap.add_argument("--report", action="store_true", help="manda telemetria e os eventos LOADED, ARRIVED e UNLOCKED")
    ap.add_argument("--once", action="store_true", help="processa no máximo uma entrega e sai")
    a = ap.parse_args()
    password = os.environ.get("GERALDO_ROBOT_PASSWORD") or os.environ.get("GERALDO_DEMO_PASSWORD")
    if not password:
        raise SystemExit("Defina GERALDO_ROBOT_PASSWORD (ou GERALDO_DEMO_PASSWORD) com a senha do usuário do robô.")
    with httpx.Client(base_url=a.api, timeout=10) as client:
        robot = MockRobot(client, a.user, password)
        robot.login()
        while True:
            task = robot.run_once(a.travel, a.report, poll_seconds=a.poll, receipt_timeout=a.timeout)
            if a.once:
                break
            if task is None:
                time.sleep(2)


if __name__ == "__main__":
    main()
