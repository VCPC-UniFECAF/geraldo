# robot/AGENTS.md — robô e simulação (dono: Samuel)

Stack: ROS 2 Jazzy + Gazebo Harmonic 8 + Nav2, **nativos** na máquina do Samuel (Pop!_OS 24.04), que também é a máquina da demo. A versão final é confirmada com a disciplina. Docker é opcional (semana 2).

## Mapa da pasta

| Pasta | Conteúdo |
|---|---|
| `hospital/` | `hospital.yaml` (fonte única da planta) e `gen_hospital.py`, que gera mundo, mapa, locais e waypoints. Testes em `hospital/tests/` |
| `scripts/` | Ambiente (`check_ros_env.sh`), malhas 3D (`export_blender_mesh.py`), parâmetros do Nav2 (`make_nav2_params.py`), teste dos 10 pontos (`nav_goal_sweep.py`) e API falsa (`fake_backend.py`). Testes em `scripts/tests/` |
| `ros2_ws/src/` | Pacotes ROS 2: `geraldo_description` (URDF, mundo, launch), `geraldo_nav` (mapa, waypoints, Nav2) e `geraldo_dispatcher` |

Testes do robô: `python -m pytest robot -q` (a raiz roda tudo com `python -m pytest tools robot -q`).
Os testes dos pacotes ROS (`ros2_ws/src/*/test/`) precisam do ROS carregado e ficam fora desse comando: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/<pacote> && python3 -m pytest test -q)`.

## Comandos

```bash
bash robot/scripts/check_ros_env.sh                      # confere o ambiente (deve imprimir AMBIENTE OK)
source /opt/ros/jazzy/setup.bash
cd robot/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch geraldo_description sim.launch.py headless:=true
```

## Rodar pelo Cursor / VS Code (sem digitar comando)

Abra a pasta `geraldo` (a raiz deste repositório) no Cursor. Depois: `Ctrl+Shift+P` → **Tasks: Run Task** e escolha (definidas em `.vscode/tasks.json`):

| Tarefa | O que faz |
|---|---|
| `GERALDO: build` | `colcon build --symlink-install` (rode depois de mudar um pacote) |
| `GERALDO: simulação + Nav2` | sobe o Gazebo com o hospital e o Nav2; o Nav2 espera o `/scan` da simulação |
| `GERALDO: varredura dos 10 pontos` | espera o Nav2 ficar ativo e navega pelos 10 pontos (uns 10 min); termina em `TODOS OS PONTOS OK` |
| `GERALDO: testes` | `python3 -m pytest tools robot -q` |

Cada tarefa carrega o ROS sozinha. Para parar: `Ctrl+Shift+P` → **Tasks: Terminate Task** (ou `Ctrl+C` no painel da tarefa). A simulação e o Nav2 têm tarefas separadas (`GERALDO: simulação`, `GERALDO: Nav2`) se você quiser reiniciar só um deles.

## Convenções

Padrões de código (SOLID, Adapter, injeção): [`docs/padroes-de-projeto.md`](../docs/padroes-de-projeto.md). No `geraldo_dispatcher`: `Navigator` (porta) com `Nav2Navigator` (adapter do `BasicNavigator`) e `FakeNavigator` nos testes; `BackendPort` com `BackendClient`; `Pose.from_dict`; um módulo por responsabilidade (`api`, `waypoints`, `dispatcher`, `node`). O `Dispatcher` recebe tudo pelo construtor.

- Referencial: `map` → `odom` → `base_link` (no chão; frente = +X). Unidades em metros e radianos.
- Rodas: `wheel_left_joint` e `wheel_right_joint` (eixo Y), separação de 0,45 m, raio de 0,10 m.
- Rodízio articulado: `caster_swivel_joint` (eixo Z, pino em x = −0,25 e z = 0,09) e `caster_wheel_joint` (eixo Y), com a roda 1,5 cm atrás do pino (trail) e encostada no chão. Se ele vibrar na simulação, o plano B é voltar à esfera sem atrito (junta fixa).
- Velocidade: o Nav2 cruza a 0,8 m/s (`CRUISE_SPEED` em `make_nav2_params.py`, no controlador e no suavizador) e o plugin de movimento do URDF aceita 0,8 m/s e 2,0 rad/s. Não suba dos 1,0 m/s sem rever as portas de 1 m e o raio de inflação.
- Malhas: 5 arquivos em `geraldo_description/meshes/` (`geraldo_body`, `roda_esq`, `roda_dir`, `rodizio_garfo`, `rodizio_roda`), um por link do URDF, exportadas do `GeraldoV3.blend` em coordenadas do `base_link` (frente = +X). O visual de cada link desfaz o deslocamento da sua junta. Para exportar de novo: `blender -b modelos-3d/geraldoV3.blend --python robot/scripts/export_blender_mesh.py`. O `.blend` está em `modelos-3d/geraldoV3.blend`; `test_export_meshes.py` regenera as malhas dele e compara com as salvas, e `test_meshes.py` confere os `.obj` sem Blender.
- Footprint do Nav2: retângulo 0,70 × 0,50 m (+10 cm de inflação).
- Tópicos e estados: `docs/contracts/ros-interfaces.md`. Não crie tópico novo sem PR no contrato.
- O mundo, o mapa e os waypoints são **gerados** por `robot/hospital/gen_hospital.py`; não edite os arquivos gerados à mão.
