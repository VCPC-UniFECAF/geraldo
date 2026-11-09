import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = json.loads((ROOT / ".vscode/tasks.json").read_text())["tasks"]
BY_LABEL = {t["label"]: t for t in TASKS}


def test_robot_tasks_exist_for_the_whole_demo():
    assert {
        "GERALDO: build",
        "GERALDO: simulação",
        "GERALDO: Nav2",
        "GERALDO: simulação + Nav2",
        "GERALDO: varredura dos 10 pontos",
        "GERALDO: testes",
    } <= set(BY_LABEL)


def test_every_script_a_task_calls_exists():
    for task in TASKS:
        for path in re.findall(r"robot/[\w/.-]+\.(?:sh|py)", task.get("command", "")):
            assert (ROOT / path).is_file(), f"{task['label']}: {path} não existe"


def test_tasks_load_ros_themselves_instead_of_relying_on_the_open_terminal():
    for label in ("GERALDO: build", "GERALDO: simulação", "GERALDO: Nav2", "GERALDO: varredura dos 10 pontos"):
        assert "source /opt/ros/jazzy/setup.bash" in BY_LABEL[label]["command"], label


def test_nav2_and_sweep_wait_for_what_they_depend_on():
    helper = ROOT / "robot/scripts/wait_for.sh"
    assert helper.is_file() and os.access(helper, os.X_OK)
    assert "wait_for.sh" in BY_LABEL["GERALDO: Nav2"]["command"]            # espera a simulação publicar /scan
    assert "wait_for.sh" in BY_LABEL["GERALDO: varredura dos 10 pontos"]["command"]   # espera o bt_navigator ativar


def test_compound_task_starts_simulation_and_nav2_in_parallel():
    both = BY_LABEL["GERALDO: simulação + Nav2"]
    assert set(both["dependsOn"]) == {"GERALDO: simulação", "GERALDO: Nav2"}
    assert both["dependsOrder"] == "parallel"
