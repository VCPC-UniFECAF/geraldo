import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SEEDS = json.loads((ROOT / "backend/seeds/locais.json").read_text(encoding="utf-8"))
WAYPOINTS = yaml.safe_load((ROOT / "robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml").read_text(encoding="utf-8"))["waypoints"]
WITH_STOP = [loc for loc in SEEDS if loc["waypoint"] is not None]  # a recepção não tem ponto de parada e não recebe entrega


def test_every_location_with_a_stop_has_a_waypoint_the_robot_knows():
    unknown = [loc["id"] for loc in WITH_STOP if loc["waypoint"] not in WAYPOINTS]
    assert unknown == [], f"locais com waypoint que o robô não conhece: {unknown}. Rode python3 robot/hospital/gen_hospital.py."


def test_every_robot_waypoint_but_the_base_belongs_to_a_location():
    assert sorted(set(WAYPOINTS) - {loc["waypoint"] for loc in WITH_STOP}) == ["base_robo"]


def test_no_two_locations_share_a_waypoint_or_an_id():
    assert len({loc["waypoint"] for loc in WITH_STOP}) == len(WITH_STOP)
    assert len({loc["id"] for loc in SEEDS}) == len(SEEDS)


def test_the_only_location_without_a_stop_is_the_reception():
    assert [loc["id"] for loc in SEEDS if loc["waypoint"] is None] == ["recepcao"]
