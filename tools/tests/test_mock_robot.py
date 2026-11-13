import json

import pytest

# O Python do sistema (testes da raiz) não tem httpx: o arquivo é pulado lá e roda no venv do backend.
httpx = pytest.importorskip("httpx")

from tools.mock_robot import MockRobot  # noqa: E402

TASK = {"id": 7, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega", "status": "EM_ROTA"}


class FakeBackend:
    """Backend de mentira (LSP: obedece ao mesmo contrato). Anota as chamadas e responde o que foi combinado."""

    def __init__(self, tasks, statuses=("ENTREGUE",), event_status=200) -> None:
        self.tasks, self.statuses, self.event_status = list(tasks), list(statuses), event_status
        self.calls: list[tuple[str, str, dict | None]] = []
        self.client = httpx.Client(transport=httpx.MockTransport(self.handle), base_url="http://api.test")

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, request.url.path, body, request.headers.get("authorization")))
        path = request.url.path
        if path == "/auth/login":
            if body["password"] != "certa":
                return httpx.Response(401, json={"detail": "Usuário ou senha incorretos. Tente de novo."})
            return httpx.Response(200, json={"access_token": "tok123", "token_type": "bearer"})
        if path == "/robot/next-task":
            return httpx.Response(200, json=self.tasks.pop(0)) if self.tasks else httpx.Response(204)
        if path == "/robot/events":
            if self.event_status == 409:
                return httpx.Response(409, json={"detail": "Evento fora de hora."})
            return httpx.Response(200, json={"id": body["delivery_id"]})
        if path == "/robot/telemetry":
            return httpx.Response(204)
        if path.startswith("/deliveries/"):
            status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return httpx.Response(200, json={"id": 7, "status": status})
        return httpx.Response(404)

    def events(self) -> list[str]:
        return [c[2]["event"] for c in self.calls if c[1] == "/robot/events"]

    def telemetry_states(self) -> list[str]:
        return [c[2]["robot_state"] for c in self.calls if c[1] == "/robot/telemetry"]

    def paths(self) -> list[str]:
        return [c[1] for c in self.calls]


def robot_for(backend, password="certa") -> MockRobot:
    robot = MockRobot(backend.client, "robo", password)
    robot.login()
    return robot


def test_login_sets_the_bearer_token():
    backend = FakeBackend([])
    robot_for(backend).next_task()
    assert backend.calls[-1][3] == "Bearer tok123"


def test_login_failure_raises_a_clear_error():
    with pytest.raises(RuntimeError, match="Login do robô falhou"):
        MockRobot(FakeBackend([]).client, "robo", "errada").login()


def test_next_task_returns_none_when_the_queue_is_empty():
    assert robot_for(FakeBackend([])).next_task() is None
    assert robot_for(FakeBackend([])).run_once(sleep=lambda s: None) is None


def test_without_report_it_only_takes_the_task_and_waits_the_travel_time():
    backend, slept = FakeBackend([TASK]), []
    assert robot_for(backend).run_once(travel_seconds=4.5, sleep=slept.append) == TASK
    assert slept == [4.5]
    assert backend.paths() == ["/auth/login", "/robot/next-task"]


def test_report_follows_the_protocol_sequence_and_unlocks_only_after_entregue():
    backend, slept = FakeBackend([TASK], statuses=("AGUARDANDO_RECEBIMENTO", "AGUARDANDO_RECEBIMENTO", "ENTREGUE")), []
    robot_for(backend).run_once(travel_seconds=1.0, report=True, sleep=slept.append, poll_seconds=2.0)
    assert backend.events() == ["LOADED", "ARRIVED", "UNLOCKED"]
    assert backend.telemetry_states() == ["A_CAMINHO", "CARREGANDO", "A_CAMINHO", "CHEGOU", "AGUARDANDO_RETIRADA", "VOLTANDO", "IDLE"]
    paths = backend.paths()
    last_status_check = max(i for i, p in enumerate(paths) if p == "/deliveries/7")
    unlocked = max(i for i, c in enumerate(backend.calls) if c[1] == "/robot/events")
    assert unlocked > last_status_check  # UNLOCKED depois da consulta que viu o ENTREGUE
    assert slept == [1.0, 1.0, 2.0, 2.0, 1.0]  # trecho 1, trecho 2, duas esperas de 2 s, volta


def test_all_events_carry_the_delivery_id_and_telemetry_matches_the_contract_fields():
    backend = FakeBackend([TASK])
    robot_for(backend).run_once(report=True, sleep=lambda s: None)
    assert all(c[2]["delivery_id"] == 7 for c in backend.calls if c[1] == "/robot/events")
    telemetry = [c[2] for c in backend.calls if c[1] == "/robot/telemetry"]
    assert all(set(t) == {"robot_state", "pose", "battery", "delivery_id", "route", "obstacles"} for t in telemetry)
    assert all(0 <= t["battery"] <= 100 for t in telemetry)
    assert [t["delivery_id"] for t in telemetry] == [7, 7, 7, 7, 7, None, None]


@pytest.mark.parametrize("status, reason", [("CANCELADA", "entrega cancelada"), ("FALHOU", "entrega falhou")])
def test_it_reports_failure_when_the_delivery_is_cancelled_or_failed_while_waiting(status, reason):
    backend = FakeBackend([TASK], statuses=(status,))
    robot_for(backend).run_once(report=True, sleep=lambda s: None)
    assert backend.events() == ["LOADED", "ARRIVED", "FAILED"]
    failed = [c[2] for c in backend.calls if c[1] == "/robot/events"][-1]
    assert failed["reason"] == reason
    assert backend.telemetry_states()[-2:] == ["VOLTANDO", "IDLE"]  # volta à base mesmo assim


def test_it_gives_up_after_the_receipt_timeout():
    backend, slept = FakeBackend([TASK], statuses=("AGUARDANDO_RECEBIMENTO",)), []
    robot_for(backend).run_once(report=True, sleep=slept.append, poll_seconds=2.0, receipt_timeout=6.0)
    assert slept.count(2.0) == 3
    assert backend.events()[-1] == "FAILED"
    assert [c[2]["reason"] for c in backend.calls if c[1] == "/robot/events"][-1] == "recebimento não confirmado a tempo"


def test_a_409_on_an_event_is_tolerated():
    backend = FakeBackend([TASK], event_status=409)
    assert robot_for(backend).run_once(report=True, sleep=lambda s: None) == TASK
