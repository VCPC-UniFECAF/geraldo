"""Gera robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml a partir do padrão do nav2_bringup.

Uso: python3 robot/scripts/make_nav2_params.py
Ajusta o footprint (0,70 x 0,50 m) e a pose inicial do AMCL (base do robô, na farmácia).
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = Path("/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml")
OUT = ROOT / "robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml"

FOOTPRINT = "[[0.35, 0.25], [0.35, -0.25], [-0.35, -0.25], [-0.35, 0.25]]"
INITIAL_POSE = {"x": 6.5, "y": 26.5, "z": 0.0, "yaw": -1.5708}
# Corredores retos e paredes lisas confundem o AMCL: a odometria simulada é boa (alphas baixos), o LiDAR vai até 12 m
# e o modelo de feixe confia mais no acerto (z_hit) do que no ruído (z_rand).
AMCL_TUNING = {
    "alpha1": 0.05, "alpha2": 0.05, "alpha3": 0.05, "alpha4": 0.05, "alpha5": 0.05,
    "laser_max_range": 12.0, "laser_min_range": 0.12, "max_beams": 120,
    "sigma_hit": 0.1, "z_hit": 0.9, "z_rand": 0.1,
    "update_min_d": 0.1, "update_min_a": 0.1,
}


def patch_params(params: dict) -> dict:
    for name in ("local_costmap", "global_costmap"):
        p = params[name][name]["ros__parameters"]
        p.pop("robot_radius", None)
        p["footprint"] = FOOTPRINT
    amcl = params["amcl"]["ros__parameters"]
    amcl["set_initial_pose"] = True
    amcl["initial_pose"] = dict(INITIAL_POSE)
    amcl["base_frame_id"] = "base_link"
    amcl.update(AMCL_TUNING)
    return _rename_frame(params, "base_footprint", "base_link")  # o robô só tem base_link (collision_monitor, docking...)


def _rename_frame(node, old: str, new: str):
    if isinstance(node, dict):
        return {k: _rename_frame(v, old, new) for k, v in node.items()}
    if isinstance(node, list):
        return [_rename_frame(v, old, new) for v in node]
    return new if node == old else node


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULTS
    params = patch_params(yaml.safe_load(src.read_text()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(params, sort_keys=False))
    print(f"gerado: {OUT}")


if __name__ == "__main__":
    main()
