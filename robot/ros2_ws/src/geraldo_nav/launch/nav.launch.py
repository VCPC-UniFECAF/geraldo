import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("geraldo_nav")
    bringup = get_package_share_directory("nav2_bringup")
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(bringup, "launch", "bringup_launch.py")),
            launch_arguments={
                "map": os.path.join(share, "maps", "hospital.yaml"),
                "params_file": os.path.join(share, "config", "nav2_params.yaml"),
                "use_sim_time": "true",
                "autostart": "true",
            }.items(),
        ),
        # Desacelera nas curvas pelo /speed_limit (pacote geraldo_dispatcher; sem exec_depend para não fechar um ciclo com o geraldo_nav)
        Node(
            package="geraldo_dispatcher",
            executable="curve_limiter",
            parameters=[{"use_sim_time": True, "v_max": 3.0, "a_lat": 1.0, "a_brake": 1.5}],
            output="screen",
        ),
    ])
