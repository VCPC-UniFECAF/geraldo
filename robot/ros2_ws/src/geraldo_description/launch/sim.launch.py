import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory("geraldo_description")
    gz_launch = os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")
    urdf = os.path.join(share, "urdf", "geraldo.urdf.xacro")
    world = os.path.join(share, "worlds", "hospital.sdf")
    bridge = os.path.join(share, "config", "bridge.yaml")

    # permite que package://geraldo_description/... seja resolvido pelo Gazebo
    resource_path = os.pathsep.join(p for p in (os.path.dirname(share), os.environ.get("GZ_SIM_RESOURCE_PATH", "")) if p)
    robot_description = ParameterValue(Command(["xacro ", urdf]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument("headless", default_value="false"),
        DeclareLaunchArgument("x", default_value="6.5"),
        DeclareLaunchArgument("y", default_value="26.5"),
        DeclareLaunchArgument("yaw", default_value="-1.5708"),
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
        # com tela: no Wayland com GPU híbrida a janela do Gazebo (Ogre2) quebra; roda via X11
        SetEnvironmentVariable("QT_QPA_PLATFORM", "xcb", condition=UnlessCondition(LaunchConfiguration("headless"))),
        SetEnvironmentVariable("EGL_PLATFORM", "", condition=UnlessCondition(LaunchConfiguration("headless"))),
        # sem tela: só o servidor, com renderização EGL para o LiDAR
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch),
            launch_arguments={"gz_args": f"-r -s --headless-rendering {world}"}.items(),
            condition=IfCondition(LaunchConfiguration("headless")),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch),
            launch_arguments={"gz_args": f"-r {world}"}.items(),
            condition=UnlessCondition(LaunchConfiguration("headless")),
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description, "use_sim_time": True}],
            output="screen",
        ),
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-world", "hospital", "-name", "geraldo", "-topic", "robot_description",
                "-x", LaunchConfiguration("x"), "-y", LaunchConfiguration("y"), "-z", "0.02",
                "-Y", LaunchConfiguration("yaw"),
            ],
            output="screen",
        ),
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            parameters=[{"config_file": bridge, "use_sim_time": True}],
            output="screen",
        ),
    ])
