import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


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
    ])
