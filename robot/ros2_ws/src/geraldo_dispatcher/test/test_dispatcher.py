import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.api import BackendClient  # noqa: E402
from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
from geraldo_dispatcher.ports import BackendPort, Navigator  # noqa: E402
from geraldo_dispatcher.waypoints import Pose, load_poses  # noqa: E402
from robot.scripts.fake_backend import DEMO_TASKS, FakeBackend  # noqa: E402

POSES = {
    "farmacia_balcao": Pose(7, 24, math.radians(270)),
    "cons1_entrega": Pose(14.5, 4, math.radians(270)),
    "banco_sangue_retirada": Pose(17, 25, math.radians(90)),
    "cc_entrega": Pose(29, 25, math.radians(90)),
}


class FakeNavigator(Navigator):  # substituto de teste do Nav2 (LSP)
    def __init__(self, reaches: bool = True) -> None:
        self.visited: list[Pose] = []
        self._reaches = reaches

    def go_to(self, pose: Pose) -> bool:
        self.visited.append(pose)
        return self._reaches


class ListBackend(BackendPort):  # substituto de teste do backend: sem HTTP
    def __init__(self, tasks: list[dict]) -> None:
        self._tasks = tasks

    def next_task(self):
        return self._tasks.pop(0) if self._tasks else None


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


def test_dispatcher_goes_to_origin_then_destination(backend):
    navigator = FakeNavigator()
    client = client_for(backend)
    client.login()
    result = Dispatcher(client, POSES, navigator, log=lambda *_: None).run_once()
    assert navigator.visited == [POSES["farmacia_balcao"], POSES["cons1_entrega"]]
    assert result["id"] == 1 and result["result"] == "CHEGOU"


def test_dispatcher_stops_when_the_robot_cannot_reach_the_origin(backend):
    navigator = FakeNavigator(reaches=False)
    client = client_for(backend)
    client.login()
    result = Dispatcher(client, POSES, navigator, log=lambda *_: None).run_once()
    assert result["result"] == "FALHOU" and result["failed_at"] == "farmacia_balcao"
    assert len(navigator.visited) == 1


def test_dispatcher_returns_none_on_an_empty_queue(backend):
    backend.tasks.clear()
    client = client_for(backend)
    client.login()
    assert Dispatcher(client, POSES, FakeNavigator(), log=lambda *_: None).run_once() is None


def test_unknown_waypoint_is_an_error_not_a_silent_skip(backend):
    client = client_for(backend)
    client.login()
    with pytest.raises(KeyError, match="farmacia_balcao"):
        Dispatcher(client, {}, FakeNavigator(), log=lambda *_: None).run_once()


def test_dispatcher_works_with_any_backend_port_without_http():
    task = {"id": 5, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cc_entrega"}
    navigator = FakeNavigator()
    result = Dispatcher(ListBackend([task]), POSES, navigator, log=lambda *_: None).run_once()
    assert result["result"] == "CHEGOU" and navigator.visited == [POSES["farmacia_balcao"], POSES["cc_entrega"]]
