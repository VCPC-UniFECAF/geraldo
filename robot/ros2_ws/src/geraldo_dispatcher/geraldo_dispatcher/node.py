import os
import threading
import time
from datetime import datetime, timezone

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav2_msgs.msg import SpeedLimit
from nav_msgs.msg import Path
from rcl_interfaces.msg import Parameter as ParameterMsg
from rcl_interfaces.msg import ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, String

from .api import BackendClient
from .dispatcher import Dispatcher
from .emergency import EmergencyStop
from .ports import BackendError, NavigationTuner, Navigator
from .profiles import NavProfile
from .states import State, StateMachine
from .telemetry import BatteryModel, TelemetryReporter, downsample, yaw_from_quaternion
from .waypoints import Pose, load_poses


class Nav2Navigator(Navigator):  # ADAPTER: traduz Pose para o NavigateToPose do Nav2 (BasicNavigator)
    def __init__(self, nav: BasicNavigator, timeout: float = 300.0, estop: EmergencyStop | None = None) -> None:
        self._nav = nav
        self._timeout = timeout
        self._estop = estop or EmergencyStop()

    def go_to(self, pose: Pose) -> bool:
        nav = self._nav
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = nav.get_clock().now().to_msg()
        goal.pose.position.x, goal.pose.position.y = pose.x, pose.y
        goal.pose.orientation.z, goal.pose.orientation.w = pose.quaternion()
        nav.goToPose(goal)
        start = time.monotonic()
        cancelled = False
        while not nav.isTaskComplete():
            if not cancelled and (self._estop.active or time.monotonic() - start > self._timeout):
                nav.cancelTask()  # o controlador para o robô ao cancelar
                cancelled = True
            time.sleep(0.5)
        # Sem esperar a conclusão, getResult() devolveria o resultado da meta anterior (SUCCEEDED) e a meta cancelada contaria como chegada.
        return not cancelled and nav.getResult() == TaskResult.SUCCEEDED


class GeraldoStateNode(Node):
    """Publica /geraldo/state e /geraldo/battery e guarda a última pose (AMCL) e a rota (/plan) para a telemetria."""

    def __init__(self, estop: EmergencyStop) -> None:
        super().__init__("geraldo_state")
        self._estop = estop
        self.pose: Pose | None = None
        self.route: list[tuple[float, float]] = []
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._state_pub = self.create_publisher(String, "/geraldo/state", latched)
        self._battery_pub = self.create_publisher(BatteryState, "/geraldo/battery", 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        self.create_subscription(Path, "/plan", self._on_plan, 10)
        self.create_subscription(Bool, "/geraldo/estop", self._on_estop, 10)

    def _on_estop(self, msg: Bool) -> None:
        if msg.data:
            self._estop.engage()
        else:
            self._estop.release()

    def publish_state(self, state: State) -> None:
        self._state_pub.publish(String(data=state.value))

    def publish_battery(self, level: float) -> None:
        self._battery_pub.publish(BatteryState(percentage=level / 100.0, present=True))

    def _on_pose(self, msg: PoseWithCovarianceStamped) -> None:
        p = msg.pose.pose
        self.pose = Pose(p.position.x, p.position.y, yaw_from_quaternion(p.orientation.z, p.orientation.w))

    def _on_plan(self, msg: Path) -> None:
        self.route = downsample([(s.pose.position.x, s.pose.position.y) for s in msg.poses], 50)


class Nav2Tuner(NavigationTuner):  # ADAPTER: traduz o perfil para o /speed_limit e o costmap local do Nav2
    def __init__(self, node: Node) -> None:
        self._node = node
        self._speed = node.create_publisher(SpeedLimit, "/speed_limit", 10)
        self._costmap = node.create_client(SetParameters, "/local_costmap/local_costmap/set_parameters")

    def apply(self, profile: NavProfile) -> None:
        self._speed.publish(SpeedLimit(percentage=False, speed_limit=profile.max_speed))
        if not self._costmap.wait_for_service(timeout_sec=2.0):
            self._node.get_logger().warning("costmap local indisponível: raio de inflação não alterado")
            return
        value = ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=profile.inflation_radius)
        request = SetParameters.Request(parameters=[ParameterMsg(name="inflation_layer.inflation_radius", value=value)])
        self._costmap.call_async(request)
        self._node.get_logger().info(f"perfil {profile.name}: {profile.max_speed} m/s, inflação {profile.inflation_radius} m")


def _every_second(reporter: TelemetryReporter) -> None:
    while rclpy.ok():
        time.sleep(1.0)
        reporter.tick(1.0)


def _login_when_available(client: BackendClient, name: str) -> None:
    """Entra no backend; se ele ainda não subiu, espera. Usuário ou senha errados (401) é erro fatal."""
    while True:
        try:
            client.login()
            return
        except BackendError as err:
            if err.status in (401, 403):
                raise SystemExit(str(err))
            print(f"{name}: {err} Tentando de novo em 5 s.", flush=True)
            time.sleep(5)


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
    _login_when_available(client, "dispatcher")
    machine, estop = StateMachine(), EmergencyStop()

    state_node = GeraldoStateNode(estop)
    machine.subscribe(state_node.publish_state)
    state_node.publish_state(machine.state)
    executor = SingleThreadedExecutor()
    executor.add_node(state_node)
    threading.Thread(target=executor.spin, daemon=True).start()

    dispatcher = Dispatcher(client, load_poses(waypoints_file), Nav2Navigator(nav, timeout=300, estop=estop),
                            machine=machine, estop=estop, tuner=Nav2Tuner(state_node))

    telemetry_client = BackendClient(api_url, "robo", password)  # cliente próprio: a telemetria roda em outra thread
    _login_when_available(telemetry_client, "telemetria")
    reporter = TelemetryReporter(
        telemetry_client, machine, BatteryModel(), pose_source=lambda: state_node.pose,
        route_source=lambda: state_node.route, delivery_source=lambda: dispatcher.delivery_id,
        on_battery=state_node.publish_battery, clock=lambda: datetime.now(timezone.utc),
    )
    threading.Thread(target=_every_second, args=(reporter,), daemon=True).start()
    try:
        while rclpy.ok():
            try:
                if dispatcher.run_once() is None:
                    time.sleep(2)
            except BackendError as err:  # backend fora do ar entre duas entregas: espera e pergunta de novo
                print(f"backend indisponível: {err}", flush=True)
                time.sleep(5)
    finally:
        rclpy.shutdown()
