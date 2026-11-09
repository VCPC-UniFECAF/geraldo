import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(not os.path.exists("/opt/ros/jazzy/setup.bash"), reason="ROS 2 Jazzy não instalado")
def test_native_environment_has_everything_the_simulation_needs():
    result = subprocess.run(["bash", str(ROOT / "robot/scripts/check_ros_env.sh")], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout
    assert "AMBIENTE OK" in result.stdout
    for needed in ("nav2_bringup", "ros_gz_sim", "ros_gz_bridge", "xacro", "diff-drive"):
        assert needed in result.stdout, needed
