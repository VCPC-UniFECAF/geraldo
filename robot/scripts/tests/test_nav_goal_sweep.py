import math
from pathlib import Path

import pytest

from robot.scripts.nav_goal_sweep import WAYPOINTS, load_stops, yaw_to_quaternion


def write_waypoints(path: Path) -> Path:
    path.write_text(
        "waypoints:\n"
        "  base_robo: {room: farmacia, x: 6.5, y: 26.5, yaw: 270}\n"
        "  farmacia_balcao: {room: farmacia, x: 7, y: 24, yaw: 270}\n"
        "  cc_entrega: {room: centro_cirurgico, x: 29, y: 25, yaw: 90}\n",
        encoding="utf-8",
    )
    return path


def test_load_stops_skips_the_robot_base_and_converts_degrees(tmp_path):
    stops = load_stops(write_waypoints(tmp_path / "w.yaml"))
    assert [s[0] for s in stops] == ["farmacia_balcao", "cc_entrega"]
    assert stops[0][1:3] == (7, 24)
    assert all(isinstance(v, float) for s in stops for v in s[1:])  # o rclpy aborta com int
    assert stops[1][3] == pytest.approx(math.pi / 2)


def test_yaw_to_quaternion():
    z, w = yaw_to_quaternion(0.0)
    assert (z, w) == (0.0, 1.0)
    z, w = yaw_to_quaternion(math.pi)
    assert z == pytest.approx(1.0) and w == pytest.approx(0.0, abs=1e-9)


@pytest.mark.skipif(not WAYPOINTS.exists(), reason="waypoints.yaml ainda não foi gerado")
def test_generated_waypoints_have_the_ten_stops():
    ids = {s[0] for s in load_stops()}
    assert ids == {
        "farmacia_balcao", "banco_sangue_retirada", "rouparia_coleta", "cc_entrega", "uti_entrega",
        "ps_entrega", "cons1_entrega", "cons2_entrega", "enf214_entrega", "enf215_entrega",
    }
