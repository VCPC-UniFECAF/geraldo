#!/usr/bin/env python3
"""Mede o robô a 3 m/s na simulação: frenagem em corredor reto, curva de 90° e desvio da maca.

Uso (simulação e Nav2 rodando, ROS carregado, robô na base):
  python3 robot/scripts/measure_speed.py freio
  python3 robot/scripts/measure_speed.py curva
  python3 robot/scripts/measure_speed.py maca              # maca já no corredor antes de a meta sair
  python3 robot/scripts/measure_speed.py maca --gap 6      # maca aparece a 6 m do robô, em plena corrida
  python3 robot/scripts/measure_speed.py base              # leva o robô de volta à base entre uma medição e outra
Cada cenário termina com uma linha `RESULTADO ...`; copie-a para docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md.
Só mede e imprime: não muda nenhum parâmetro do robô.
"""
import argparse
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WAYPOINTS = ROOT / "robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml"
SPAWN = ROOT / "robot/scripts/spawn_stretcher.sh"

CRUISE = 3.0          # m/s
STOPPED = 0.05        # m/s: abaixo disso o robô parou
FAST_ENOUGH = 2.85    # m/s: o freio só é medido a partir daqui
BRAKE_GOAL = (42.0, 29.0, 0.0)  # fim do corredor norte (y = 29): uns 35 m de reta depois da porta da farmácia
BRAKE_FROM_X = 25.0   # m: o comando de parada sai depois de o robô passar daqui já a velocidade de cruzeiro
TOUCH_DISTANCE = 0.35  # m: meio comprimento do robô; o centro a menos disso da borda da maca conta como encostar
DOOR_LINE = (28.0, 28.0)  # (x, y) da porta norte do centro cirúrgico: x >= 28 e y <= 28 = já virou para dentro dela
GOAL_TIMEOUT = 240.0  # s por meta


@dataclass(frozen=True)
class Sample:
    t: float           # s (relógio da simulação, vindo do /odom)
    ox: float          # m, posição no odom (para distâncias percorridas)
    oy: float
    v: float           # m/s, velocidade linear
    w: float           # rad/s, velocidade angular
    mx: float | None   # m, posição no mapa (último /amcl_pose); None até o AMCL publicar
    my: float | None
    scan_min: float    # m, menor leitura do /scan até agora nesta amostra (inf se ainda não há)


@dataclass(frozen=True)
class Box:
    cx: float
    cy: float
    hx: float  # meia largura em x
    hy: float  # meia largura em y


# A maca (worlds/maca.sdf): caixa de 2,0 x 0,8 m em (23, 29) girada 90°, então ocupa x 22,6..23,4 e y 28..30.
MACA = Box(23.0, 29.0, 0.4, 1.0)


def stopping(samples: list[Sample], t_cmd: float) -> tuple[float, float] | None:
    """(distância em m, tempo em s) do instante `t_cmd` até a primeira amostra com v < 0,05 m/s; None se nunca parou."""
    after = [s for s in samples if s.t >= t_cmd]
    if not after:
        return None
    start = after[0]
    for s in after[1:]:
        if s.v < STOPPED:
            return math.hypot(s.ox - start.ox, s.oy - start.oy), s.t - start.t
    return None


def peak_speed(samples: list[Sample]) -> float:
    return max((abs(s.v) for s in samples), default=0.0)


def peak_lateral_acceleration(samples: list[Sample]) -> float:
    """Maior |v x w| (m/s²): a aceleração lateral de um robô diferencial."""
    return max((abs(s.v * s.w) for s in samples), default=0.0)


def speed_entering(samples: list[Sample], x_min: float, y_max: float) -> float | None:
    """Velocidade na primeira amostra com x >= x_min e y <= y_max no mapa (a entrada de uma porta); None se não passou."""
    for s in samples:
        if s.mx is not None and s.my is not None and s.mx >= x_min and s.my <= y_max:
            return abs(s.v)
    return None


def distance_to_box(x: float, y: float, box: Box) -> float:
    """Distância de (x, y) à borda do retângulo (0 se estiver dentro)."""
    dx, dy = max(abs(x - box.cx) - box.hx, 0.0), max(abs(y - box.cy) - box.hy, 0.0)
    return math.hypot(dx, dy)


def closest_approach(samples: list[Sample], box: Box) -> float:
    """Menor distância do centro do robô à borda da caixa durante a corrida (inf se o AMCL não publicou)."""
    return min((distance_to_box(s.mx, s.my, box) for s in samples if s.mx is not None and s.my is not None),
               default=math.inf)


def waypoint(name: str) -> tuple[float, float, float]:
    """(x, y, yaw em graus) de um ponto do waypoints.yaml."""
    w = yaml.safe_load(WAYPOINTS.read_text(encoding="utf-8"))["waypoints"][name]
    return float(w["x"]), float(w["y"]), float(w["yaw"])


class Recorder:
    """Assina /odom, /amcl_pose e /scan no nó do navegador e guarda uma Sample a cada /odom."""

    def __init__(self, node) -> None:
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from nav_msgs.msg import Odometry
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import LaserScan

        self.samples: list[Sample] = []
        self._map: tuple[float, float] | None = None
        self._scan_min = math.inf
        node.create_subscription(Odometry, "/odom", self._on_odom, 50)
        node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        node.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)

    def _on_pose(self, msg) -> None:
        self._map = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def _on_scan(self, msg) -> None:
        valid = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
        if valid:
            self._scan_min = min(self._scan_min, min(valid))

    def _on_odom(self, msg) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        mx, my = self._map if self._map else (None, None)
        self.samples.append(Sample(t, msg.pose.pose.position.x, msg.pose.pose.position.y, msg.twist.twist.linear.x,
                                   msg.twist.twist.angular.z, mx, my, self._scan_min))

    @property
    def latest(self) -> Sample | None:
        return self.samples[-1] if self.samples else None


def goal_pose(nav, x: float, y: float, yaw_deg: float):
    from geometry_msgs.msg import PoseStamped

    goal = PoseStamped()
    goal.header.frame_id = "map"
    goal.header.stamp = nav.get_clock().now().to_msg()
    goal.pose.position.x, goal.pose.position.y = float(x), float(y)
    yaw = math.radians(yaw_deg)
    goal.pose.orientation.z, goal.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    return goal


def run_goal(nav, recorder: Recorder, goal, on_tick=lambda sample: None) -> bool:
    """Manda a meta e espera terminar (chamando `on_tick` a cada passo). True se o Nav2 chegou."""
    from nav2_simple_commander.robot_navigator import TaskResult

    nav.goToPose(goal)
    start = time.monotonic()
    while not nav.isTaskComplete():  # isTaskComplete gira o nó por 0,1 s, então o Recorder recebe as mensagens
        if recorder.latest is not None:
            on_tick(recorder.latest)
        if time.monotonic() - start > GOAL_TIMEOUT:
            nav.cancelTask()
            break
    return nav.getResult() == TaskResult.SUCCEEDED


def freio(nav, recorder: Recorder) -> str:
    import rclpy

    nav.goToPose(goal_pose(nav, *BRAKE_GOAL))
    start, t_cmd = time.monotonic(), None
    while t_cmd is None and time.monotonic() - start < GOAL_TIMEOUT and not nav.isTaskComplete():
        s = recorder.latest
        if s is not None and s.mx is not None and s.mx >= BRAKE_FROM_X and s.v >= FAST_ENOUGH:
            t_cmd = s.t
            v_cmd = s.v
            nav.cancelTask()  # é o que o dispatcher faz na parada de emergência
    if t_cmd is None:
        status = nav.getResult()
        nav.cancelTask()
        return (f"RESULTADO freio nao_atingiu_{CRUISE:.1f}_m_s pico={peak_speed(recorder.samples):.2f} m/s "
                f"fim_da_meta={status.name if hasattr(status, 'name') else status}")
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline and not (recorder.latest and recorder.latest.t > t_cmd and recorder.latest.v < STOPPED):
        rclpy.spin_once(nav, timeout_sec=0.05)
    result = stopping(recorder.samples, t_cmd)
    if result is None:
        return f"RESULTADO freio v_no_comando={v_cmd:.2f} m/s nao_parou_em_20_s"
    return f"RESULTADO freio v_no_comando={v_cmd:.2f} m/s distancia_ate_parar={result[0]:.2f} m tempo_ate_parar={result[1]:.2f} s"


def curva(nav, recorder: Recorder) -> str:
    x, y, yaw = waypoint("cc_entrega")  # sai da farmácia (90° para leste), corre o corredor e vira 90° para a porta do CC
    reached = run_goal(nav, recorder, goal_pose(nav, x, y, yaw))
    samples = recorder.samples
    door = speed_entering(samples, *DOOR_LINE)
    door_text = f"{door:.2f} m/s" if door is not None else "nao_passou"
    return (f"RESULTADO curva chegou={reached} v_max={peak_speed(samples):.2f} m/s "
            f"aceleracao_lateral_max={peak_lateral_acceleration(samples):.2f} m/s2 velocidade_na_porta={door_text} "
            f"menor_leitura_do_lidar={min((s.scan_min for s in samples), default=math.inf):.2f} m")


def base(nav, recorder: Recorder) -> str:
    x, y, yaw = waypoint("base_robo")
    reached = run_goal(nav, recorder, goal_pose(nav, x, y, yaw))
    return f"RESULTADO base chegou={reached}"


def set_stretcher(on: bool) -> None:
    subprocess.run(["bash", str(SPAWN), "on" if on else "off"], check=True, capture_output=True, text=True)


def maca(nav, recorder: Recorder, gap: float | None) -> str:
    x, y, yaw = waypoint("cc_entrega")
    spawned = gap is None
    if spawned:
        set_stretcher(True)
    try:
        def tick(sample: Sample) -> None:
            nonlocal spawned
            if not spawned and sample.mx is not None and sample.mx >= MACA.cx - MACA.hx - gap:
                set_stretcher(True)
                spawned = True

        reached = run_goal(nav, recorder, goal_pose(nav, x, y, yaw), tick)
    finally:
        set_stretcher(False)
    samples = recorder.samples
    closest = closest_approach(samples, MACA)
    how = "ja_no_corredor" if gap is None else f"surgiu_a_{gap:g}_m"
    return (f"RESULTADO maca {how} chegou={reached} v_max={peak_speed(samples):.2f} m/s "
            f"menor_distancia_a_borda_da_maca={closest:.2f} m encostou={closest <= TOUCH_DISTANCE}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cenario", choices=["freio", "curva", "maca", "base"])
    ap.add_argument("--gap", type=float, default=None, help="só em `maca`: metros entre o robô e a maca quando ela surge")
    args = ap.parse_args()

    import rclpy
    from nav2_simple_commander.robot_navigator import BasicNavigator

    rclpy.init()
    nav = BasicNavigator()
    nav.initial_pose_received = True  # o AMCL já nasce na base (nav2_params.yaml)
    nav.waitUntilNav2Active()
    recorder = Recorder(nav)
    try:
        if args.cenario == "freio":
            print(freio(nav, recorder))
        elif args.cenario == "curva":
            print(curva(nav, recorder))
        elif args.cenario == "base":
            print(base(nav, recorder))
        else:
            print(maca(nav, recorder, args.gap))
    finally:
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
