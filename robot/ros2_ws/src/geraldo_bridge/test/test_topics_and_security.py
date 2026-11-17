from pathlib import Path

from geraldo_bridge import main as main_module
from geraldo_bridge.ros_adapter import PUBLISHED, SUBSCRIBED

PACKAGE = Path(__file__).resolve().parents[1] / "geraldo_bridge"


def test_the_bridge_touches_only_the_contract_topics():
    assert PUBLISHED == ("/geraldo/estop",)
    assert set(SUBSCRIBED) == {
        "/geraldo/state",
        "/geraldo/battery",
        "/amcl_pose",
        "/plan",
        "/scan",
        "/range/front_c",
        "/range/front_l45",
        "/range/front_r45",
        "/range/rear_l135",
        "/range/rear_r135",
    }


def test_no_source_file_mentions_the_velocity_command():
    for source in PACKAGE.glob("*.py"):
        assert "cmd_vel" not in source.read_text(encoding="utf-8"), source.name


def test_importing_main_does_not_need_ros_or_uvicorn():
    assert callable(main_module.main)
