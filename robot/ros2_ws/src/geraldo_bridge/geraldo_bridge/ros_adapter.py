import threading

from .convert import (
    RANGE_NAMES,
    battery_percent,
    pose_from_amcl,
    route_from_path,
    scan_to_dict,
)
from .ports import RosPort
from .state import BridgeState

# Contrato (docs/contracts/ros-interfaces.md): são os únicos tópicos que a ponte toca. Nada de comando de movimento.
PUBLISHED = ("/geraldo/estop",)
SUBSCRIBED = (
    "/geraldo/state",
    "/geraldo/battery",
    "/amcl_pose",
    "/plan",
    "/scan",
    *(f"/range/{name}" for name in RANGE_NAMES),
)
ESTOP_REPEATS = (0.0, 0.2, 0.4)  # como `ros2 topic pub -r 5 -t 3`: o dispatcher não perde a mensagem


class RclpyRosPort(RosPort):  # ADAPTER: traduz as mensagens do rclpy para os dicts do BridgeState
    def __init__(self) -> None:
        self._rclpy = None
        self._node = None
        self._executor = None
        self._thread: threading.Thread | None = None
        self._estop_pub = None
        self._bool = None
        self._stopping = threading.Event()

    def start(self, state: BridgeState) -> None:
        import rclpy
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from nav_msgs.msg import Path
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
        from sensor_msgs.msg import BatteryState, LaserScan
        from std_msgs.msg import Bool, String

        rclpy.init()
        node = Node("geraldo_bridge")
        # o dispatcher publica o estado "preso" (transient_local); quem entra depois ainda recebe o último
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(String, "/geraldo/state", lambda m: state.update_robot_state(m.data), latched)
        node.create_subscription(BatteryState, "/geraldo/battery", lambda m: state.update_battery(battery_percent(m)), 10)
        node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", lambda m: state.update_pose(pose_from_amcl(m)), latched)
        node.create_subscription(Path, "/plan", lambda m: state.update_route(route_from_path(m)), 10)
        node.create_subscription(LaserScan, "/scan", lambda m: state.update_scan(scan_to_dict(m)), qos_profile_sensor_data)
        for name in RANGE_NAMES:
            node.create_subscription(
                LaserScan, f"/range/{name}", lambda m, n=name: state.update_range(n, scan_to_dict(m)), qos_profile_sensor_data
            )
        self._estop_pub = node.create_publisher(Bool, "/geraldo/estop", 10)
        self._rclpy, self._node, self._bool = rclpy, node, Bool
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(node)
        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()

    def publish_estop(self, active: bool) -> None:
        for delay in ESTOP_REPEATS:
            threading.Timer(delay, self._publish_once, args=(active,)).start()

    def _publish_once(self, active: bool) -> None:
        if self._stopping.is_set() or self._estop_pub is None:  # as repetições ainda pendentes morrem junto com a ponte
            return
        self._estop_pub.publish(self._bool(data=active))

    def stop(self) -> None:
        if self._rclpy is None:
            return
        self._stopping.set()
        self._executor.shutdown()
        self._node.destroy_node()
        if self._rclpy.ok():
            self._rclpy.shutdown()
        self._rclpy = None
