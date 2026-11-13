import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.ports import TelemetryPort  # noqa: E402
from geraldo_dispatcher.states import State, StateMachine  # noqa: E402
from geraldo_dispatcher.telemetry import (  # noqa: E402
    BatteryModel, TelemetryReporter, build_telemetry, downsample, yaw_from_quaternion,
)
from geraldo_dispatcher.waypoints import Pose  # noqa: E402

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def test_battery_drains_while_travelling_and_recharges_when_idle():
    battery = BatteryModel(level=50.0)
    assert battery.step(State.A_CAMINHO, 10) == pytest.approx(49.5)
    assert battery.step(State.IDLE, 10) == pytest.approx(54.5)


def test_battery_drains_slowly_while_waiting():
    assert BatteryModel(level=50.0).step(State.AGUARDANDO_RETIRADA, 10) == pytest.approx(49.95)


def test_battery_stays_between_zero_and_one_hundred():
    assert BatteryModel(level=99.9).step(State.IDLE, 10) == 100.0
    assert BatteryModel(level=0.1).step(State.VOLTANDO, 100) == 0.0


def test_build_telemetry_follows_the_contract():
    body = build_telemetry(State.A_CAMINHO, Pose(1.0, 2.0, 0.5), 87.26, 7, [(1, 2), (3, 4)], [(5, 6, 0.3)], NOW)
    spec = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))["components"]["schemas"]["Telemetry"]
    assert set(spec["required"]) <= set(body) <= set(spec["properties"])
    assert body["robot_state"] in spec["properties"]["robot_state"]["enum"]
    assert body["pose"] == {"x": 1.0, "y": 2.0, "yaw": 0.5}
    assert body["battery"] == 87.3 and body["delivery_id"] == 7
    assert body["route"] == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert body["obstacles"] == [{"x": 5, "y": 6, "radius": 0.3}]
    assert body["updated_at"] == "2026-11-13T12:00:00+00:00"


def test_downsample_keeps_the_ends_and_respects_the_limit():
    points = [(i, 0) for i in range(200)]
    small = downsample(points, limit=50)
    assert len(small) == 50 and small[0] == (0, 0) and small[-1] == (199, 0)
    assert downsample(points[:10], limit=50) == points[:10]


def test_yaw_from_quaternion_is_the_inverse_of_pose_quaternion():
    for yaw in (math.pi / 2, -math.pi / 2, 0.0, 3.0):
        z, w = Pose(0, 0, yaw).quaternion()
        assert yaw_from_quaternion(z, w) == pytest.approx(yaw)


class Sink(TelemetryPort):
    def __init__(self, fails=False):
        self.bodies, self.fails = [], fails

    def send_telemetry(self, body):
        if self.fails:
            raise OSError("sem rede")
        self.bodies.append(body)


def reporter(sink, pose=Pose(1, 2, 0.5), logs=None, levels=None):
    return TelemetryReporter(
        sink, StateMachine(), BatteryModel(level=80.0), pose_source=lambda: pose,
        route_source=lambda: [(1, 2), (3, 4)], delivery_source=lambda: 7,
        on_battery=(levels if levels is not None else []).append, clock=lambda: NOW,
        log=(logs if logs is not None else []).append,
    )


def test_tick_sends_state_pose_battery_route_and_delivery():
    sink, levels = Sink(), []
    reporter(sink, levels=levels).tick(1.0)
    body = sink.bodies[0]
    assert body["robot_state"] == "IDLE" and body["battery"] == 80.5 and body["delivery_id"] == 7
    assert levels == [80.5]


def test_tick_does_nothing_until_the_pose_is_known():
    sink = Sink()
    reporter(sink, pose=None).tick(1.0)
    assert sink.bodies == []


def test_a_telemetry_failure_is_logged_and_never_stops_the_robot():
    logs = []
    reporter(Sink(fails=True), logs=logs).tick(1.0)
    assert logs and "telemetria não enviada" in logs[0]
