import math
from types import SimpleNamespace as NS

import pytest

from geraldo_bridge.convert import (
    battery_percent,
    closest_range,
    pose_from_amcl,
    route_from_path,
    scan_to_dict,
    scan_to_map_points,
    yaw_from_quaternion,
)


def amcl(x, y, yaw):
    q = NS(z=math.sin(yaw / 2), w=math.cos(yaw / 2))
    return NS(pose=NS(pose=NS(position=NS(x=x, y=y), orientation=q)))


def scan(ranges, angle_min=0.0, angle_increment=0.1, range_min=0.05, range_max=10.0):
    return {"angle_min": angle_min, "angle_increment": angle_increment, "range_min": range_min, "range_max": range_max, "ranges": ranges}


def test_yaw_from_quaternion_round_trips():
    for yaw in (0.0, 1.0, -2.0, 3.0):
        assert yaw_from_quaternion(math.sin(yaw / 2), math.cos(yaw / 2)) == pytest.approx(yaw)


def test_pose_from_amcl_rounds_to_millimetres():
    assert pose_from_amcl(amcl(6.5004, 26.5, -math.pi / 2)) == {"x": 6.5, "y": 26.5, "yaw": -1.571}


def test_route_from_path_keeps_the_ends_and_limits_the_size():
    poses = [NS(pose=NS(position=NS(x=float(i), y=0.0))) for i in range(1000)]
    route = route_from_path(NS(poses=poses), limit=50)
    assert len(route) == 50
    assert route[0] == {"x": 0.0, "y": 0.0}
    assert route[-1] == {"x": 999.0, "y": 0.0}


def test_route_from_path_of_a_short_plan_is_untouched():
    poses = [NS(pose=NS(position=NS(x=1.0, y=2.0)))]
    assert route_from_path(NS(poses=poses)) == [{"x": 1.0, "y": 2.0}]


def test_battery_percent_comes_from_a_0_to_1_fraction():
    assert battery_percent(NS(percentage=0.875)) == 87.5


def test_scan_to_dict_copies_the_fields_the_bridge_uses():
    msg = NS(angle_min=-1.0, angle_increment=0.5, range_min=0.1, range_max=5.0, ranges=(1.0, 2.0))
    assert scan_to_dict(msg) == scan([1.0, 2.0], angle_min=-1.0, angle_increment=0.5, range_min=0.1, range_max=5.0)


def test_closest_range_ignores_infinite_nan_and_out_of_range_beams():
    assert closest_range(scan([math.inf, 3.0, math.nan, 1.234, 0.01, 10.0])) == 1.23


def test_closest_range_is_none_when_nothing_was_hit():
    assert closest_range(scan([math.inf, math.inf])) is None


def test_scan_points_use_the_pose_and_the_lidar_offset():
    # robô em (1, 2) olhando para +X; o lidar fica 0,275 m à frente do base_link
    points = scan_to_map_points(scan([1.0]), {"x": 1.0, "y": 2.0, "yaw": 0.0})
    assert points[0]["x"] == pytest.approx(2.275, abs=0.01)
    assert points[0]["y"] == pytest.approx(2.0, abs=0.01)


def test_scan_points_rotate_with_the_robot_yaw():
    points = scan_to_map_points(scan([1.0]), {"x": 1.0, "y": 2.0, "yaw": math.pi / 2})
    assert points[0]["x"] == pytest.approx(1.0, abs=0.01)
    assert points[0]["y"] == pytest.approx(2.0 + 0.275 + 1.0, abs=0.01)


def test_scan_points_follow_the_beam_angle():
    points = scan_to_map_points(scan([1.0, 1.0], angle_min=0.0, angle_increment=math.pi / 2), {"x": 0.0, "y": 0.0, "yaw": 0.0})
    assert points[1]["x"] == pytest.approx(0.275, abs=0.01)
    assert points[1]["y"] == pytest.approx(1.0, abs=0.01)


def test_scan_points_are_limited_and_skip_misses():
    ranges = [1.0 if i % 2 else math.inf for i in range(2000)]
    points = scan_to_map_points(scan(ranges), {"x": 0.0, "y": 0.0, "yaw": 0.0}, limit=100)
    assert len(points) == 100
