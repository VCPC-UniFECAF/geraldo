import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.api import BackendClient  # noqa: E402
from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
from geraldo_dispatcher.ports import BackendPort, Navigator  # noqa: E402
from geraldo_dispatcher.states import State, StateMachine  # noqa: E402
from geraldo_dispatcher.waypoints import Pose, load_poses  # noqa: E402
from robot.scripts.fake_backend import DEMO_TASKS, FakeBackend  # noqa: E402

POSES = {
    "base_robo": Pose(6.5, 26.5, math.radians(270)),
    "farmacia_balcao": Pose(7, 24, math.radians(270)),
    "cons1_entrega": Pose(14.5, 4, math.radians(270)),
    "banco_sangue_retirada": Pose(17, 25, math.radians(90)),
    "cc_entrega": Pose(29, 25, math.radians(90)),
}
TASK = {"id": 5, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cc_entrega"}
WAITING = "AGUARDANDO_RECEBIMENTO"


class FakeNavigator(Navigator):  # substituto de teste do Nav2 (LSP)
    def __init__(self, fails_at=()) -> None:
        self.visited: list[Pose] = []
        self._fails_at = set(fails_at)

    def go_to(self, pose: Pose) -> bool:
        self.visited.append(pose)
        return pose not in self._fails_at


class ScriptedBackend(BackendPort):  # substituto de teste do backend: sem HTTP, com os status da entrega roteirizados
    def __init__(self, tasks, statuses=("ENTREGUE",)) -> None:
        self._tasks, self._statuses = list(tasks), list(statuses)
        self.events: list[tuple[str, str | None]] = []

    def next_task(self):
        return self._tasks.pop(0) if self._tasks else None

    def send_event(self, delivery_id, event, reason=None):
        self.events.append((event, reason))
        return True

    def delivery_status(self, delivery_id):
        return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]


def run(backend, navigator=None, poses=POSES, **kwargs):
    machine, history, sleeps = StateMachine(), [], []
    machine.subscribe(history.append)
    dispatcher = Dispatcher(backend, poses, navigator or FakeNavigator(), machine=machine, sleep=sleeps.append,
                            log=lambda *_: None, **kwargs)
    return dispatcher.run_once(), history, sleeps


@pytest.fixture
def backend():
    server = FakeBackend([dict(t) for t in DEMO_TASKS]).start()
    yield server
    server.stop()


def client_for(backend, password="robo-local"):
    return BackendClient(backend.url, "robo", password)


def test_load_poses_converts_degrees_to_radians(tmp_path):
    path = tmp_path / "w.yaml"
    path.write_text("waypoints:\n  a: {room: x, x: 1.5, y: 2.5, yaw: 90}\n", encoding="utf-8")
    pose = load_poses(path)["a"]
    assert (pose.x, pose.y) == (1.5, 2.5)
    assert pose.yaw == pytest.approx(math.pi / 2)
    z, w = pose.quaternion()
    assert z == pytest.approx(math.sin(math.pi / 4)) and w == pytest.approx(math.cos(math.pi / 4))


def test_pose_from_dict_converts_degrees_to_radians():
    pose = Pose.from_dict({"x": 1, "y": 2, "yaw": 180})
    assert (pose.x, pose.y) == (1.0, 2.0) and pose.yaw == pytest.approx(math.pi)
    assert all(isinstance(v, float) for v in (pose.x, pose.y))  # o rclpy aborta com int


def test_login_failure_has_a_clear_message(backend):
    with pytest.raises(RuntimeError, match="Login do robô falhou"):
        client_for(backend, "errada").login()


def test_next_task_returns_tasks_in_order_then_none(backend):
    client = client_for(backend)
    client.login()
    assert client.next_task()["id"] == 1
    assert client.next_task()["id"] == 2
    assert client.next_task() is None


def test_client_logs_in_again_when_the_token_expires(backend):
    client = client_for(backend)
    client.login()
    backend.expire_token()
    assert client.next_task()["id"] == 1
    assert backend.calls.count("/auth/login") == 2


def test_a_delivery_walks_the_states_and_tells_the_backend_in_order():
    scripted = ScriptedBackend([TASK])
    navigator = FakeNavigator()
    result, history, sleeps = run(scripted, navigator)
    assert history == [State.A_CAMINHO, State.CARREGANDO, State.A_CAMINHO, State.CHEGOU,
                       State.AGUARDANDO_RETIRADA, State.VOLTANDO, State.IDLE]
    assert scripted.events == [("LOADED", None), ("ARRIVED", None), ("UNLOCKED", None)]
    assert navigator.visited == [POSES["farmacia_balcao"], POSES["cc_entrega"], POSES["base_robo"]]
    assert result["id"] == 5 and result["result"] == "ENTREGUE"
    assert sleeps == []


def test_it_polls_the_delivery_until_the_requester_confirms():
    scripted = ScriptedBackend([TASK], statuses=[WAITING, WAITING, "ENTREGUE"])
    result, _, sleeps = run(scripted)
    assert result["result"] == "ENTREGUE" and sleeps == [2.0, 2.0]


def test_a_cancelled_delivery_ends_in_failure_and_goes_home():
    scripted = ScriptedBackend([TASK], statuses=["CANCELADA"])
    navigator = FakeNavigator()
    result, history, _ = run(scripted, navigator)
    assert result["result"] == "FALHOU" and result["failed_at"] == "cc_entrega" and result["reason"] == "entrega cancelada"
    assert scripted.events[-1] == ("FAILED", "entrega cancelada")
    assert history[-2:] == [State.VOLTANDO, State.IDLE] and navigator.visited[-1] == POSES["base_robo"]


def test_it_gives_up_waiting_for_the_receipt_after_the_timeout():
    scripted = ScriptedBackend([TASK], statuses=[WAITING])
    result, _, sleeps = run(scripted, receipt_timeout=6.0)
    assert sleeps == [2.0, 2.0, 2.0]
    assert result["reason"] == "recebimento não confirmado a tempo"
    assert scripted.events[-1] == ("FAILED", "recebimento não confirmado a tempo")


def test_unreachable_origin_reports_failure_and_returns_home():
    scripted = ScriptedBackend([TASK])
    navigator = FakeNavigator(fails_at=[POSES["farmacia_balcao"]])
    result, history, _ = run(scripted, navigator)
    assert result["result"] == "FALHOU" and result["failed_at"] == "farmacia_balcao"
    assert scripted.events == [("FAILED", "não chegou à origem")]
    assert history == [State.A_CAMINHO, State.VOLTANDO, State.IDLE]
    assert navigator.visited == [POSES["farmacia_balcao"], POSES["base_robo"]]


def test_unreachable_destination_reports_failure_after_loading():
    scripted = ScriptedBackend([TASK])
    result, history, _ = run(scripted, FakeNavigator(fails_at=[POSES["cc_entrega"]]))
    assert result["failed_at"] == "cc_entrega"
    assert scripted.events == [("LOADED", None), ("FAILED", "não chegou ao destino")]
    assert history == [State.A_CAMINHO, State.CARREGANDO, State.A_CAMINHO, State.VOLTANDO, State.IDLE]


def test_the_delivery_id_is_known_only_during_the_delivery():
    seen = []

    class Spy(FakeNavigator):
        def go_to(self, pose):
            seen.append(dispatcher.delivery_id)
            return super().go_to(pose)

    dispatcher = Dispatcher(ScriptedBackend([TASK]), POSES, Spy(), sleep=lambda _: None, log=lambda *_: None)
    assert dispatcher.delivery_id is None
    dispatcher.run_once()
    assert seen == [5, 5, 5] and dispatcher.delivery_id is None


def test_it_returns_none_on_an_empty_queue():
    result, history, _ = run(ScriptedBackend([]))
    assert result is None and history == []


@pytest.mark.parametrize("missing", ["farmacia_balcao", "cc_entrega", "base_robo"])
def test_a_waypoint_missing_from_the_map_is_an_error_not_a_silent_skip(missing):
    poses = {k: v for k, v in POSES.items() if k != missing}
    with pytest.raises(KeyError, match=missing):
        run(ScriptedBackend([TASK]), poses=poses)


def test_the_whole_flow_works_against_the_http_backend(backend):
    client = client_for(backend)
    client.login()
    result, _, _ = run(client)
    assert result["id"] == 1 and result["result"] == "ENTREGUE"
    assert [e["event"] for e in backend.events] == ["LOADED", "ARRIVED", "UNLOCKED"]
