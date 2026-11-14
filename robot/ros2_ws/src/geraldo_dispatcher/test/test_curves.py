import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.curves import curvature, curve_speed_limit, remaining_path, resample  # noqa: E402


def line(length, y=0.0, x0=0.0, step=0.05):
    return [(x0 + i * step, y) for i in range(int(length / step) + 1)]


def corner(before=5.0, after=5.0, step=0.05):
    """Reta de `before` m ao longo de +x seguida de uma quina de 90° e `after` m ao longo de +y."""
    first = [(i * step, 0.0) for i in range(int(before / step) + 1)]
    second = [(before, i * step) for i in range(1, int(after / step) + 1)]
    return first + second


def arc(radius, angle=math.pi / 2, step=0.05):
    n = int(radius * angle / step)
    return [(radius * math.sin(i * step / radius), radius * (1 - math.cos(i * step / radius))) for i in range(n + 1)]


def test_resample_spaces_the_points_by_arc_length_and_keeps_the_first():
    points = resample(line(2.0), step=0.5)
    assert points[0] == (0.0, 0.0) and len(points) == 5
    assert [round(x, 3) for x, _ in points] == [0.0, 0.5, 1.0, 1.5, 2.0]
    assert resample([]) == []


def test_curvature_is_the_inverse_of_the_circle_radius_and_zero_on_a_line():
    assert curvature((0, 0), (1, 0), (2, 0)) == 0.0
    assert curvature((0, 0), (1, 0), (1, 0)) == 0.0
    r = 2.0
    pts = [(r * math.sin(t), r * (1 - math.cos(t))) for t in (0.0, 0.3, 0.6)]
    assert curvature(*pts) == pytest.approx(1 / r)


def test_a_straight_corridor_allows_the_full_speed():
    assert curve_speed_limit(line(20.0)) == 3.0


def test_a_gentle_arc_far_enough_does_not_slow_the_robot():
    assert curve_speed_limit(arc(radius=20.0)) == 3.0  # sqrt(1,0 x 20) = 4,5 m/s > 3,0


def test_a_tight_arc_limits_the_speed_to_sqrt_of_lateral_acceleration_over_curvature():
    # raio de 1 m e a_lat = 1 m/s² dão 1 m/s (a_brake = 0 isola o efeito da curva, sem distância de frenagem)
    assert curve_speed_limit(arc(radius=1.0), a_lat=1.0, a_brake=0.0) == pytest.approx(1.0, abs=0.05)
    assert curve_speed_limit(arc(radius=1.0), a_lat=2.0, a_brake=0.0) == pytest.approx(math.sqrt(2.0), abs=0.05)


def test_a_corner_ahead_brakes_gradually_so_the_robot_can_stop_in_time():
    near = curve_speed_limit(corner(before=1.0))
    mid = curve_speed_limit(corner(before=2.0))
    far = curve_speed_limit(corner(before=5.0))
    assert near < mid < far == 3.0
    # quina de 90° medida a cada 0,5 m: curvatura 2,83 1/m => 0,59 m/s; a 1 m dela: sqrt(0,59² + 2 x 1,5 x 1,0)
    assert near == pytest.approx(math.sqrt(0.594 ** 2 + 2 * 1.5 * 1.0), abs=0.1)


def test_a_corner_beyond_the_lookahead_is_ignored():
    assert curve_speed_limit(corner(before=15.0)) == 3.0


def test_the_limit_never_drops_below_the_minimum_speed():
    assert curve_speed_limit(corner(before=0.5, after=2.0), v_min=0.3) >= 0.3
    assert curve_speed_limit([(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1), (0, 0)]) >= 0.3


def test_the_limit_never_exceeds_the_maximum_speed_and_short_paths_are_safe():
    assert curve_speed_limit(line(20.0), v_max=2.0) == 2.0
    assert curve_speed_limit([]) == 3.0
    assert curve_speed_limit([(0.0, 0.0)]) == 3.0


def test_remaining_path_starts_at_the_point_nearest_to_the_robot():
    path = line(2.0, step=0.5)
    assert remaining_path(path, 1.05, 0.2) == [(1.0, 0.0), (1.5, 0.0), (2.0, 0.0)]
    assert remaining_path([], 0, 0) == []
