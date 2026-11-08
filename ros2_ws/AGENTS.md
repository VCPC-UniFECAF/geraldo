# ros2_ws/AGENTS.md — robô e simulação (dono: Samuel)

Stack: ROS 2 Jazzy + Gazebo Harmonic 8 + Nav2, **nativos** na máquina do Samuel (Pop!_OS 24.04), que também é a máquina da demo. A versão final é confirmada com a disciplina. Docker é opcional (semana 2).

## Comandos

```bash
bash tools/check_ros_env.sh                      # confere o ambiente (deve imprimir AMBIENTE OK)
source /opt/ros/jazzy/setup.bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch geraldo_description sim.launch.py headless:=true
```

## Convenções

- Referencial: `map` → `odom` → `base_link` (no chão; frente = +X). Unidades em metros e radianos.
- Rodas: `wheel_left_joint` e `wheel_right_joint` (eixo Y), separação de 0,45 m, raio de 0,10 m.
- Footprint do Nav2: retângulo 0,70 × 0,50 m (+10 cm de inflação).
- Tópicos e estados: `docs/contracts/ros-interfaces.md`. Não crie tópico novo sem PR no contrato.
- O mundo, o mapa e os waypoints são **gerados** por `tools/gen_hospital.py`; não edite os arquivos gerados à mão.
