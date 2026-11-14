import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.msg import SpeedLimit
from nav_msgs.msg import Path
from rclpy.node import Node

from .curves import A_BRAKE, A_LAT, V_MAX, curve_speed_limit, remaining_path


class CurveLimiter(Node):
    """Publica em /speed_limit a velocidade que a curvatura do /plan à frente permite (a conta está em curves.py)."""

    def __init__(self) -> None:
        super().__init__("curve_limiter")
        self._v_max = self.declare_parameter("v_max", V_MAX).value
        self._a_lat = self.declare_parameter("a_lat", A_LAT).value
        self._a_brake = self.declare_parameter("a_brake", A_BRAKE).value
        self._path: list[tuple[float, float]] = []
        self._pose: tuple[float, float] | None = None
        self._last: float | None = None
        self._pub = self.create_publisher(SpeedLimit, "/speed_limit", 10)
        self.create_subscription(Path, "/plan", self._on_plan, 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        self.create_timer(0.1, self._tick)

    def _on_plan(self, msg: Path) -> None:
        self._path = [(s.pose.position.x, s.pose.position.y) for s in msg.poses]

    def _on_pose(self, msg: PoseWithCovarianceStamped) -> None:
        self._pose = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def _tick(self) -> None:
        if self._pose is None:
            return
        ahead = remaining_path(self._path, *self._pose)
        limit = round(curve_speed_limit(ahead, v_max=self._v_max, a_lat=self._a_lat, a_brake=self._a_brake), 2)
        if limit != self._last:  # o Nav2 guarda o último limite recebido: só publica quando muda
            self._last = limit
            self._pub.publish(SpeedLimit(percentage=False, speed_limit=limit))


def main() -> None:
    rclpy.init()
    rclpy.spin(CurveLimiter())
    rclpy.shutdown()
