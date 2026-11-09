import os
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

from .api import BackendClient
from .dispatcher import Dispatcher
from .ports import Navigator
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
    dispatcher = Dispatcher(client, load_poses(waypoints_file), Nav2Navigator(nav, timeout=300))
    try:
        while rclpy.ok():
            if dispatcher.run_once() is None:
                time.sleep(2)
    finally:
        rclpy.shutdown()
