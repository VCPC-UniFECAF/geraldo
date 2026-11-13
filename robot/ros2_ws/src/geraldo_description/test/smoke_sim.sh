#!/usr/bin/env bash
# Sobe a simulação sem tela, confere /scan e /odom e anda 3 segundos com /cmd_vel.
set -euo pipefail

# setsid: o launch vira líder de um grupo de processos, e o trap derruba o grupo inteiro (Gazebo, ponte e publisher)
setsid ros2 launch geraldo_description sim.launch.py headless:=true > /tmp/sim.log 2>&1 &
LAUNCH_PID=$!
trap 'kill -INT -- -$LAUNCH_PID 2>/dev/null || true; sleep 3; kill -KILL -- -$LAUNCH_PID 2>/dev/null || true' EXIT

timeout 120 bash -c 'until ros2 topic list | grep -q "^/scan$"; do sleep 2; done'
timeout 30 ros2 topic echo --once /scan --field ranges > /dev/null
for sensor in front_c front_l45 front_r45 rear_l135 rear_r135; do
  timeout 30 ros2 topic echo --once "/range/$sensor" --field ranges > /dev/null
done
timeout 30 ros2 topic echo --once /odom --field pose.pose.position > /tmp/odom0.txt

ros2 topic pub -t 30 -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}" > /dev/null
timeout 30 ros2 topic echo --once /odom --field pose.pose.position > /tmp/odom1.txt

if diff -q /tmp/odom0.txt /tmp/odom1.txt > /dev/null; then
  echo "SMOKE FALHOU: o robô não se mexeu"; exit 1
fi
echo "SMOKE OK"
