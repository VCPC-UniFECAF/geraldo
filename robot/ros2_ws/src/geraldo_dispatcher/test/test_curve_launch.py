import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

NAV_LAUNCH = ROOT / "robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py"
SETUP = ROOT / "robot/ros2_ws/src/geraldo_dispatcher/setup.py"


def test_the_nav_launch_starts_the_curve_limiter_with_the_cruise_speed():
    src = NAV_LAUNCH.read_text(encoding="utf-8")
    ast.parse(src)
    assert 'package="geraldo_dispatcher"' in src and 'executable="curve_limiter"' in src
    assert '"v_max": 3.0' in src and '"a_lat": 1.0' in src and '"use_sim_time": True' in src


def test_the_curve_limiter_is_an_installed_executable():
    assert "curve_limiter = geraldo_dispatcher.curve_node:main" in SETUP.read_text(encoding="utf-8")
