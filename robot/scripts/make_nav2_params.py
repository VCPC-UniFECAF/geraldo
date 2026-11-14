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
# m/s: velocidade de cruzeiro única (pedido do líder, ~10 km/h), para qualquer prioridade. Antes 0,5, 0,8 e 1,0.
# É também o teto do plugin de movimento do URDF. A desaceleração em curvas vem do nó curve_limiter pelo /speed_limit.
CRUISE_SPEED = 3.0
# O MPPI só chega à velocidade de cruzeiro se (1) a janela do costmap local cobrir o horizonte (56 passos x 0,05 s = 2,8 s,
# ou 8,4 m a 3 m/s; com a janela de 3 m o robô não passava de uns 0,5 m/s), (2) o caminho podado for tão longo quanto o
# horizonte e (3) os críticos de caminho olharem longe e a amostragem tiver ruído para acelerar. Valores achados na
# simulação em 13/11/2026 (corredor reto a 3,0 m/s); a medição da Task 9 do plano 1 os confirma ou ajusta.
LOCAL_COSTMAP_SIZE = 18      # m (largura e altura da janela do costmap local)
MPPI_TUNING = {"vx_std": 0.5, "prune_distance": 9.0}
CRITIC_TUNING = {
    "PathFollowCritic": {"offset_from_furthest": 60, "cost_weight": 15.0},
    "PathAlignCritic": {"offset_from_furthest": 100},
}


def patch_params(params: dict) -> dict:
    for name in ("local_costmap", "global_costmap"):
        p = params[name][name]["ros__parameters"]
        p.pop("robot_radius", None)
        p["footprint"] = FOOTPRINT
    # O costmap global mantém o obstacle_layer (padrão do nav2_bringup): sem ele o planejador não vê obstáculos novos,
    # como a maca do corredor norte, e o robô para na frente dela em vez de replanejar pela cruz central.
    # Validado em 12/11/2026: com a camada ligada a varredura dos 10 pontos continua em TODOS OS PONTOS OK.
    follow = params["controller_server"]["ros__parameters"]["FollowPath"]
    follow["vx_max"] = CRUISE_SPEED
    follow.update(MPPI_TUNING)
    for critic, values in CRITIC_TUNING.items():
        follow.setdefault(critic, {}).update(values)
    local = params["local_costmap"]["local_costmap"]["ros__parameters"]
    local["width"] = local["height"] = LOCAL_COSTMAP_SIZE
    params["velocity_smoother"]["ros__parameters"]["max_velocity"][0] = CRUISE_SPEED   # senão o suavizador corta o controlador
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
