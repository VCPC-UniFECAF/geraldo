import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEMO = ROOT / "robot/scripts/demo.sh"


def test_demo_script_is_executable_and_valid_bash():
    assert DEMO.is_file() and os.access(DEMO, os.X_OK)
    subprocess.run(["bash", "-n", str(DEMO)], check=True)


def test_demo_script_isolates_ros_and_never_kills_by_name():
    text = DEMO.read_text(encoding="utf-8")
    assert 'ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"' in text and 'GZ_PARTITION="${GZ_PARTITION:-verif}"' in text
    assert "pkill" not in text and "pgrep -f" not in text
    assert "kill -9 -- " in text  # o gz sim e o dispatcher só morrem com -9
    assert "grep -q '^active'" in text  # "inactive" também contém "active"
    for piece in ("uvicorn app.main:app", "VITE_API_URL", "sim.launch.py", "nav.launch.py", "geraldo_dispatcher dispatcher", "--headless"):
        assert piece in text, piece


def test_demo_script_rejects_unknown_options_before_starting_anything():
    result = subprocess.run(["bash", str(DEMO), "--nada"], capture_output=True, text=True)
    assert result.returncode == 2 and "uso:" in result.stderr


def test_the_demo_script_is_listed_by_the_robot_agents_file():
    assert "demo.sh" in (ROOT / "robot/AGENTS.md").read_text(encoding="utf-8")
