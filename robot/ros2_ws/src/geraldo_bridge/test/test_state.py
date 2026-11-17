import math
from datetime import datetime, timezone

import pytest

from geraldo_bridge.convert import RANGE_NAMES
from geraldo_bridge.state import BridgeState


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def make():
    clock = Clock()
    return BridgeState(clock=clock, now=lambda: NOW), clock


def scan(ranges):
    return {"angle_min": 0.0, "angle_increment": 0.1, "range_min": 0.05, "range_max": 10.0, "ranges": ranges}


def test_empty_snapshot_has_the_exact_shape_and_is_stale():
    state, _ = make()
    assert state.snapshot() == {
        "robot_state": None,
        "pose": None,
        "battery": None,
        "route": [],
        "scan": [],
        "ranges": {name: None for name in RANGE_NAMES},
        "estop": False,
        "stale": True,
        "updated_at": "2026-11-13T12:00:00+00:00",
    }


def test_updates_show_up_in_the_snapshot_and_clear_stale():
    state, _ = make()
    state.update_robot_state("A_CAMINHO")
    state.update_battery(87.5)
    state.update_pose({"x": 1.0, "y": 2.0, "yaw": 0.0})
    state.update_route([{"x": 1.0, "y": 2.0}])
    snap = state.snapshot()
    assert (snap["robot_state"], snap["battery"], snap["stale"]) == ("A_CAMINHO", 87.5, False)
    assert snap["pose"] == {"x": 1.0, "y": 2.0, "yaw": 0.0}
    assert snap["route"] == [{"x": 1.0, "y": 2.0}]


def test_snapshot_goes_stale_after_three_seconds_of_silence():
    state, clock = make()
    state.update_battery(50.0)
    clock.t += 2.9
    assert state.snapshot()["stale"] is False
    clock.t += 0.2
    assert state.snapshot()["stale"] is True


def test_scan_without_a_pose_has_no_map_points():
    state, _ = make()
    state.update_scan(scan([1.0, 2.0]))
    assert state.snapshot()["scan"] == []


def test_scan_with_a_pose_becomes_map_points():
    state, _ = make()
    state.update_pose({"x": 0.0, "y": 0.0, "yaw": 0.0})
    state.update_scan(scan([1.0, math.inf]))
    assert len(state.snapshot()["scan"]) == 1


def test_range_sensors_keep_only_the_closest_distance():
    state, _ = make()
    state.update_range("front_c", scan([2.0, 0.8, 1.5]))
    assert state.snapshot()["ranges"]["front_c"] == 0.8


def test_unknown_range_sensor_is_an_error_in_portuguese():
    state, _ = make()
    with pytest.raises(ValueError, match="Sensor de alcance desconhecido"):
        state.update_range("front_x", scan([1.0]))


def test_estop_is_kept_but_does_not_count_as_a_message_from_ros():
    state, _ = make()
    state.update_estop(True)
    snap = state.snapshot()
    assert snap["estop"] is True and snap["stale"] is True


def test_snapshot_is_a_copy():
    state, _ = make()
    state.update_route([{"x": 1.0, "y": 1.0}])
    state.snapshot()["route"].clear()
    assert state.snapshot()["route"] == [{"x": 1.0, "y": 1.0}]
