# robot/AGENTS.md — robô e simulação (dono: Samuel)

Stack: ROS 2 Jazzy + Gazebo Harmonic 8 + Nav2, **nativos** na máquina do Samuel (Pop!_OS 24.04), que também é a máquina da demo. A versão final é confirmada com a disciplina. Docker é opcional (semana 2).

## Mapa da pasta

| Pasta | Conteúdo |
|---|---|
| `hospital/` | `hospital.yaml` (fonte única da planta) e `gen_hospital.py`, que gera mundo, mapa, locais e waypoints. Testes em `hospital/tests/` |
| `scripts/` | Ambiente (`check_ros_env.sh`), malha 3D (`export_blender_mesh.py`), parâmetros do Nav2 (`make_nav2_params.py`), teste dos 10 pontos (`nav_goal_sweep.py`) e API falsa (`fake_backend.py`). Testes em `scripts/tests/` |
| `ros2_ws/src/` | Pacotes ROS 2: `geraldo_description` (URDF, mundo, launch), `geraldo_nav` (mapa, waypoints, Nav2) e `geraldo_dispatcher` |

Testes do robô: `python -m pytest robot -q` (a raiz roda tudo com `python -m pytest tools robot -q`).

## Comandos

```bash
bash robot/scripts/check_ros_env.sh                      # confere o ambiente (deve imprimir AMBIENTE OK)
source /opt/ros/jazzy/setup.bash
cd robot/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch geraldo_description sim.launch.py headless:=true
```

## Convenções

Padrões de código (SOLID, Adapter, injeção): [`docs/padroes-de-projeto.md`](../docs/padroes-de-projeto.md). No `geraldo_dispatcher`: `Navigator` (porta) com `Nav2Navigator` (adapter do `BasicNavigator`) e `FakeNavigator` nos testes; `BackendPort` com `BackendClient`; `Pose.from_dict`; um módulo por responsabilidade (`api`, `waypoints`, `dispatcher`, `node`). O `Dispatcher` recebe tudo pelo construtor.

- Referencial: `map` → `odom` → `base_link` (no chão; frente = +X). Unidades em metros e radianos.
- Rodas: `wheel_left_joint` e `wheel_right_joint` (eixo Y), separação de 0,45 m, raio de 0,10 m.
- Footprint do Nav2: retângulo 0,70 × 0,50 m (+10 cm de inflação).
- Tópicos e estados: `docs/contracts/ros-interfaces.md`. Não crie tópico novo sem PR no contrato.
- O mundo, o mapa e os waypoints são **gerados** por `robot/hospital/gen_hospital.py`; não edite os arquivos gerados à mão.
