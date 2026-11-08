#!/usr/bin/env python3
"""Manda o robô a cada ponto de parada do hospital e confere se o Nav2 chega (valida as portas de 1,0 m).

Uso (com a simulação e o Nav2 rodando, ROS carregado):
  python3 robot/scripts/nav_goal_sweep.py [--timeout 180]
Sai com 0 só se todos os pontos forem alcançados.
"""
import argparse
import math
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WAYPOINTS = ROOT / "robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml"


def load_stops(path=WAYPOINTS) -> list[tuple[str, float, float, float]]:
    """(id, x, y, yaw em radianos) de todos os pontos, exceto a base do robô."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["waypoints"]
    # float(): o YAML devolve int para "7" e as mensagens ROS exigem float (senão o rclpy aborta)
    return [(wid, float(w["x"]), float(w["y"]), math.radians(w["yaw"])) for wid, w in data.items() if wid != "base_robo"]


def yaw_to_quaternion(yaw: float) -> tuple[float, float]:
    """(z, w) do quaternion de uma rotação em torno de Z."""
    return math.sin(yaw / 2), math.cos(yaw / 2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=float, default=180.0, help="segundos por ponto")
    args = ap.parse_args()

    import rclpy
    from geometry_msgs.msg import PoseStamped
    from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

    rclpy.init()
    nav = BasicNavigator()
    # o AMCL já nasce na base (nav2_params.yaml): sem isto o BasicNavigator republica a pose (0, 0) e perde a localização
    nav.initial_pose_received = True
    nav.waitUntilNav2Active()
    failed = []
    for wid, x, y, yaw in load_stops():
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = nav.get_clock().now().to_msg()
        goal.pose.position.x, goal.pose.position.y = x, y
        goal.pose.orientation.z, goal.pose.orientation.w = yaw_to_quaternion(yaw)
        nav.goToPose(goal)
        start = time.monotonic()
        while not nav.isTaskComplete():
            if time.monotonic() - start > args.timeout:
                nav.cancelTask()
                break
            time.sleep(0.5)
        ok = nav.getResult() == TaskResult.SUCCEEDED
        print(f"{'ok    ' if ok else 'FALHOU'} {wid:24s} {time.monotonic() - start:5.0f}s")
        if not ok:
            failed.append(wid)
    rclpy.shutdown()
    print("TODOS OS PONTOS OK" if not failed else f"FALHARAM: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
