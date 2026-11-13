import os
import threading
import time
from datetime import datetime, timezone

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Path
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

from .api import BackendClient
from .dispatcher import Dispatcher
from .ports import Navigator
from .states import State, StateMachine
from .telemetry import BatteryModel, TelemetryReporter, downsample, yaw_from_quaternion
from .waypoints import Pose, load_poses


class Nav2Navigator(Navigator):  # ADAPTER: traduz Pose para o NavigateToPose do Nav2 (BasicNavigator)
    def __init__(self, nav: BasicNavigator, timeout: float = 300.0) -> None:
        self._nav = nav
        self._timeout = timeout

    def go_to(self, pose: Pose) -> bool:
        nav = self._nav
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = nav.get_clock().now().to_msg()
        goal.pose.position.x, goal.pose.position.y = pose.x, pose.y
        goal.pose.orientation.z, goal.pose.orientation.w = pose.quaternion()
        nav.goToPose(goal)
        start = time.monotonic()
        while not nav.isTaskComplete():
            if time.monotonic() - start > self._timeout:
                nav.cancelTask()
                break
            time.sleep(0.5)
        return nav.getResult() == TaskResult.SUCCEEDED


class GeraldoStateNode(Node):
    """Publica /geraldo/state e /geraldo/battery e guarda a última pose (AMCL) e a rota (/plan) para a telemetria."""

    def __init__(self) -> None:
        super().__init__("geraldo_state")
        self.pose: Pose | None = None
        self.route: list[tuple[float, float]] = []
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._state_pub = self.create_publisher(String, "/geraldo/state", latched)
        self._battery_pub = self.create_publisher(BatteryState, "/geraldo/battery", 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        self.create_subscription(Path, "/plan", self._on_plan, 10)

    def publish_state(self, state: State) -> None:
        self._state_pub.publish(String(data=state.value))

    def publish_battery(self, level: float) -> None:
        self._battery_pub.publish(BatteryState(percentage=level / 100.0, present=True))

    def _on_pose(self, msg: PoseWithCovarianceStamped) -> None:
        p = msg.pose.pose
        self.pose = Pose(p.position.x, p.position.y, yaw_from_quaternion(p.orientation.z, p.orientation.w))

    def _on_plan(self, msg: Path) -> None:
        self.route = downsample([(s.pose.position.x, s.pose.position.y) for s in msg.poses], 50)


def _every_second(reporter: TelemetryReporter) -> None:
    while rclpy.ok():
        time.sleep(1.0)
        reporter.tick(1.0)


def main() -> None:
    password = os.environ.get("GERALDO_ROBOT_PASSWORD") or os.environ.get("GERALDO_DEMO_PASSWORD")
    if not password:
        raise SystemExit("Defina GERALDO_ROBOT_PASSWORD (ou GERALDO_DEMO_PASSWORD) com a senha do usuário do robô.")
    api_url = os.environ.get("GERALDO_API_URL", "http://localhost:8000")

    rclpy.init()
    nav = BasicNavigator()
    nav.initial_pose_received = True  # o AMCL já tem a pose inicial; não deixe o BasicNavigator republicar (0, 0)
    nav.waitUntilNav2Active()
    waypoints_file = os.path.join(get_package_share_directory("geraldo_nav"), "config", "waypoints.yaml")
    client = BackendClient(api_url, "robo", password)
    client.login()
    machine = StateMachine()
    dispatcher = Dispatcher(client, load_poses(waypoints_file), Nav2Navigator(nav, timeout=300), machine=machine)

    state_node = GeraldoStateNode()
    machine.subscribe(state_node.publish_state)
    state_node.publish_state(machine.state)
    executor = SingleThreadedExecutor()
    executor.add_node(state_node)
    threading.Thread(target=executor.spin, daemon=True).start()

    telemetry_client = BackendClient(api_url, "robo", password)  # cliente próprio: a telemetria roda em outra thread
    telemetry_client.login()
    reporter = TelemetryReporter(
        telemetry_client, machine, BatteryModel(), pose_source=lambda: state_node.pose,
        route_source=lambda: state_node.route, delivery_source=lambda: dispatcher.delivery_id,
        on_battery=state_node.publish_battery, clock=lambda: datetime.now(timezone.utc),
    )
    threading.Thread(target=_every_second, args=(reporter,), daemon=True).start()
    try:
        while rclpy.ok():
            if dispatcher.run_once() is None:
                time.sleep(2)
    finally:
        rclpy.shutdown()
