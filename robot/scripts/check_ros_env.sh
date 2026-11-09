#!/usr/bin/env bash
# Confere se o ambiente nativo tem tudo o que a simulação do G.E.R.A.L.D.O. precisa.
# (sem `set -u`: o setup.bash do ROS usa variáveis não definidas)
source /opt/ros/jazzy/setup.bash 2>/dev/null || { echo "FALTA   ROS 2 Jazzy em /opt/ros/jazzy"; exit 1; }
missing=0
for pkg in nav2_bringup nav2_amcl nav2_map_server nav2_msgs nav2_simple_commander ros_gz_sim ros_gz_bridge robot_state_publisher xacro; do
  if ros2 pkg prefix "$pkg" >/dev/null 2>&1; then echo "ok      $pkg"; else echo "FALTA   $pkg"; missing=1; fi
done
version=$(gz sim --versions 2>/dev/null | head -1)
case "$version" in
  8.*) echo "ok      gazebo $version (Harmonic)" ;;
  *) echo "FALTA   Gazebo Harmonic 8.x (achei: ${version:-nada})"; missing=1 ;;
esac
if ls /opt/ros/jazzy/opt/gz_sim_vendor/lib/gz-sim-8/plugins/libgz-sim8-diff-drive-system.so >/dev/null 2>&1; then
  echo "ok      plugin diff-drive do Gazebo"
else
  echo "FALTA   plugin diff-drive do Gazebo"; missing=1
fi
if [ "$missing" -eq 0 ]; then
  echo "AMBIENTE OK"
else
  echo "AMBIENTE INCOMPLETO. Para o Nav2: sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup"
  exit 1
fi
