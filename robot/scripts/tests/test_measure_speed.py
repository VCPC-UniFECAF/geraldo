import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from robot.scripts.measure_speed import (  # noqa: E402
    MACA, Box, Sample, closest_approach, distance_to_box, peak_lateral_acceleration, peak_speed, speed_entering,
    stopping, waypoint,
)


def sample(t, ox=0.0, v=0.0, w=0.0, mx=None, my=None, scan_min=math.inf):
    return Sample(t, ox, 0.0, v, w, mx, my, scan_min)


def test_stopping_measures_distance_and_time_from_the_command_to_standstill():
    run = [sample(0.0, 0.0, 3.0), sample(1.0, 3.0, 3.0), sample(1.5, 4.5, 2.0), sample(2.0, 5.5, 0.9), sample(2.5, 5.9, 0.04)]
    assert stopping(run, t_cmd=1.0) == pytest.approx((2.9, 1.5))   # de x = 3,0 até x = 5,9, em 1,5 s


def test_stopping_is_none_when_the_robot_never_stops_or_there_is_nothing_after_the_command():
    assert stopping([sample(0.0, 0.0, 3.0), sample(1.0, 3.0, 3.0)], t_cmd=0.0) is None
    assert stopping([sample(0.0)], t_cmd=5.0) is None


def test_peaks_ignore_direction():
    run = [sample(0, v=-0.4, w=1.0), sample(1, v=2.0, w=0.5), sample(2, v=1.0, w=-1.9)]
    assert peak_speed(run) == 2.0
    assert peak_lateral_acceleration(run) == pytest.approx(1.9)
    assert peak_speed([]) == 0.0 and peak_lateral_acceleration([]) == 0.0


def test_speed_entering_a_door_uses_the_first_sample_past_the_line():
    run = [sample(0, v=3.0, mx=20.0, my=29.0), sample(1, v=2.0, mx=28.6, my=29.0), sample(2, v=1.2, mx=28.9, my=27.5),
           sample(3, v=0.5, mx=29.0, my=26.0)]
    assert speed_entering(run, x_min=28.0, y_max=28.0) == 1.2
    assert speed_entering(run[:2], x_min=28.0, y_max=28.0) is None
    assert speed_entering([sample(0, v=1.0)], x_min=0.0, y_max=100.0) is None   # sem AMCL ainda


def test_distance_to_box_is_zero_inside_and_euclidean_outside():
    box = Box(0.0, 0.0, 1.0, 2.0)
    assert distance_to_box(0.5, 1.0, box) == 0.0
    assert distance_to_box(3.0, 0.0, box) == pytest.approx(2.0)
    assert distance_to_box(4.0, 6.0, box) == pytest.approx(math.hypot(3.0, 4.0))


def test_closest_approach_takes_the_minimum_over_the_run():
    run = [sample(0, mx=15.0, my=29.0), sample(1, mx=21.0, my=29.0), sample(2, mx=18.0, my=29.0), sample(3)]
    assert closest_approach(run, MACA) == pytest.approx(22.6 - 21.0)
    assert closest_approach([sample(0)], MACA) == math.inf


def test_the_stretcher_box_matches_the_sdf_of_the_world():
    sdf = (ROOT / "robot/ros2_ws/src/geraldo_description/worlds/maca.sdf").read_text(encoding="utf-8")
    assert "<pose>23.000 29.000 0 0 0 1.5708</pose>" in sdf and "<size>2.000 0.800 0.900</size>" in sdf
    assert (MACA.cx, MACA.cy, MACA.hx, MACA.hy) == (23.0, 29.0, 0.4, 1.0)   # girada 90°: 0,8 m em x e 2,0 m em y


def test_the_goal_is_read_from_the_waypoints_file():
    assert waypoint("cc_entrega") == (29.0, 25.0, 90.0)
