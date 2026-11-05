# G.E.R.A.L.D.O. — Semana 1 (Samuel): robô e simulação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ter o robô simulado no Gazebo, dentro do hospital gerado do `hospital.yaml`, respondendo a `/cmd_vel`, publicando `/scan` e `/odom`, e navegando com o Nav2 até um ponto do mapa.

**Architecture:** Uma imagem Docker única (ROS 2 Jazzy + Gazebo Harmonic + Nav2) para todos. O pacote `geraldo_description` tem o URDF (xacro), a malha exportada do Blender, o mundo gerado e o launch do Gazebo com a ponte ROS↔Gazebo. O pacote `geraldo_nav` tem o mapa gerado, os waypoints e o launch do Nav2, com parâmetros gerados por script a partir do padrão do `nav2_bringup`.

**Tech Stack:** ROS 2 Jazzy, Gazebo Harmonic (`gz sim`), `ros_gz_sim`, `ros_gz_bridge`, Nav2, xacro, Docker, Blender (só para exportar a malha), pytest.

**Spec:** `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` (seções 4.1 e 8)

**Pré-requisito:** Tarefas 1 e 4 do plano `2026-11-05-semana1-samuel-fundacao.md` (repo, modelo em `assets/blender/` e `tools/gen_hospital.py` com o hospital gerado).

## Global Constraints

- Versões: ROS 2 **Jazzy** + Gazebo **Harmonic** (confirmar com a disciplina; se a disciplina usar outra, só o `Dockerfile` e os nomes `gz-sim-*` mudam).
- Referencial `map → odom → base_link`; `base_link` no chão, frente = +X (spec §8).
- Rodas: separação de **0,45 m** (y = ±0,225), raio **0,10 m**, eixo Y; eixo das rodas em x = **+0,10 m**. Rodízio traseiro de raio 0,04 m em x = −0,30 m (spec §8).
- Footprint do Nav2: retângulo **0,70 × 0,50 m** com 10 cm de inflação (spec §4.1).
- Tópicos e estados: `docs/contracts/ros-interfaces.md`. Nenhum tópico novo sem PR no contrato.
- Mundo, mapa e waypoints são **gerados** por `tools/gen_hospital.py`; não editar à mão.
- O Gazebo **não usa o `.blend`**: usa a malha visual exportada e colisão simples (spec §8).
- Gazebo sem interface (`headless`) para desenvolver; a demo roda na máquina Linux do líder (spec §7).
- Sem segredos no repositório.

---

### Task 1: Imagem Docker única

**Files:**
- Create: `docker/Dockerfile.ros`, `docker/compose.yml`, `docker/compose.gui.yml`, `docker/smoke_image.sh`

**Interfaces:**
- Produces: serviço `ros` do compose (`docker compose -f docker/compose.yml run --rm ros <comando>`), com `/ws` = `ros2_ws/`, `/repo/tools` e `/repo/hospital` montados; `ROS_DOMAIN_ID=42`.

- [ ] **Step 1: Escrever o teste de fumaça (falha primeiro)**

Create `docker/smoke_image.sh`:

```bash
#!/usr/bin/env bash
# Confirma que a imagem tem tudo que o projeto precisa.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker/compose.yml build
found=$(docker compose -f docker/compose.yml run --rm -T ros bash -lc \
  'ros2 pkg list | grep -E "^(nav2_bringup|ros_gz_sim|ros_gz_bridge|xacro|robot_state_publisher)$" | sort')
echo "$found"
test "$(echo "$found" | wc -l)" -eq 5 || { echo "FALTAM PACOTES"; exit 1; }
docker compose -f docker/compose.yml run --rm -T ros bash -lc 'gz sim --versions | head -1'
echo "IMAGEM OK"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `bash docker/smoke_image.sh`
Expected: FAIL (compose não existe).

- [ ] **Step 3: Escrever o Dockerfile e o compose**

Create `docker/Dockerfile.ros`:

```dockerfile
FROM osrf/ros:jazzy-desktop-full

RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-navigation2 \
      ros-jazzy-nav2-bringup \
      ros-jazzy-ros-gz \
      ros-jazzy-xacro \
      ros-jazzy-robot-state-publisher \
      python3-pytest python3-yaml python3-numpy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
CMD ["bash"]
```

Create `docker/compose.yml`:

```yaml
services:
  ros:
    build:
      context: ..
      dockerfile: docker/Dockerfile.ros
    image: geraldo/ros:jazzy
    working_dir: /ws
    volumes:
      - ../ros2_ws:/ws
      - ../tools:/repo/tools
      - ../hospital:/repo/hospital
    environment:
      - ROS_DOMAIN_ID=42
    extra_hosts:
      - "host.docker.internal:host-gateway"   # o dispatcher acessa a API do backend que roda no host
    stdin_open: true
    tty: true
```

Create `docker/compose.gui.yml` (só para Linux com tela; some com `headless:=false`):

```yaml
services:
  ros:
    environment:
      - DISPLAY=${DISPLAY}
      - QT_X11_NO_MITSHM=1
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
    devices:
      - /dev/dri:/dev/dri
```

Uso com tela: `docker compose -f docker/compose.yml -f docker/compose.gui.yml run --rm ros bash` (antes, `xhost +local:docker` no host).

- [ ] **Step 4: Rodar e ver passar**

Run: `bash docker/smoke_image.sh`
Expected: lista 5 pacotes (`nav2_bringup`, `robot_state_publisher`, `ros_gz_bridge`, `ros_gz_sim`, `xacro`), uma linha de versão do Gazebo (`8.x`, Harmonic) e `IMAGEM OK`. A primeira build demora (baixa a imagem base).

- [ ] **Step 5: Commit**

```bash
git add docker
git commit -m "feat: imagem Docker unica (ROS 2 Jazzy, Gazebo Harmonic, Nav2)"
```

Avise Erik, Vieira e Pedro: "imagem pronta; só quem mexe no robô precisa dela".

---

### Task 2: Malha do robô exportada do Blender

**Files:**
- Create: `tools/export_blender_mesh.py`
- Create (gerados): `ros2_ws/src/geraldo_description/meshes/geraldo_body.obj`, `ros2_ws/src/geraldo_description/meshes/geraldo_body.mtl`
- Test: `tools/tests/test_export_mesh.py`

**Interfaces:**
- Consumes: `assets/blender/geraldo2.blend` (coleção `GERALDO`; objetos de roda começam com `roda_`, `disco_`, `tampa_`, rodízio com `rodizio_`).
- Produces: `meshes/geraldo_body.obj` — chassi, baú, sensores e LiDAR em metros, frente = +X, Z para cima, origem em `base_link` (as rodas e o rodízio **não** entram: viram primitivas no URDF).

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_export_mesh.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OBJ = ROOT / "ros2_ws/src/geraldo_description/meshes/geraldo_body.obj"


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender não instalado")
def test_export_creates_the_body_mesh_in_the_right_frame():
    subprocess.run(
        ["blender", "-b", str(ROOT / "assets/blender/geraldo2.blend"), "--python", str(ROOT / "tools/export_blender_mesh.py")],
        check=True, capture_output=True, text=True, timeout=300,
    )
    verts = [l.split() for l in OBJ.read_text().splitlines() if l.startswith("v ")]
    assert len(verts) > 1000
    xs = [float(v[1]) for v in verts]
    ys = [float(v[2]) for v in verts]
    zs = [float(v[3]) for v in verts]
    assert 0.30 < max(xs) < 0.45 and -0.45 < min(xs) < -0.30   # frente em +X, traseira em -X
    assert 0.20 < max(ys) < 0.30 and -0.30 < min(ys) < -0.20   # largura ~0,50 m
    assert 0.40 < max(zs) < 0.55 and min(zs) > 0.03            # sobe até ~0,47 m; rodas fora da malha
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_export_mesh.py -q`
Expected: FAIL (`export_blender_mesh.py` não existe) ou `skipped` se não houver Blender na máquina; nesse caso peça ao Samuel para rodar.

- [ ] **Step 3: Implementar o script de exportação**

Create `tools/export_blender_mesh.py`:

```python
"""Exporta a malha do corpo do G.E.R.A.L.D.O. para o Gazebo (OBJ).

Uso: blender -b assets/blender/geraldo2.blend --python tools/export_blender_mesh.py
Rodas e rodízio ficam de fora: o URDF as descreve com primitivas para poderem girar.
"""
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ros2_ws", "src", "geraldo_description", "meshes")
SKIP_PREFIXES = ("roda_", "disco_", "tampa_", "rodizio_")

os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
count = 0
for obj in bpy.data.collections["GERALDO"].objects:
    if obj.type == "MESH" and not obj.name.startswith(SKIP_PREFIXES):
        obj.select_set(True)
        count += 1
assert count > 20, f"poucos objetos selecionados: {count}"

bpy.ops.wm.obj_export(
    filepath=os.path.join(OUT, "geraldo_body.obj"),
    export_selected_objects=True,
    apply_modifiers=True,
    export_materials=True,
    # a "frente" do exportador é o -Y do Blender; com NEGATIVE_Y e Z os eixos do arquivo ficam idênticos aos da cena (frente = +X)
    forward_axis="NEGATIVE_Y",
    up_axis="Z",
    global_scale=1.0,
)
print("EXPORT_OK", count)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tools/tests/test_export_mesh.py -q`
Expected: `1 passed`. Confira o tamanho: `ls -la ros2_ws/src/geraldo_description/meshes/` (cerca de 1–3 MB).

- [ ] **Step 5: Commit**

```bash
git add tools/export_blender_mesh.py tools/tests/test_export_mesh.py ros2_ws/src/geraldo_description/meshes
git commit -m "feat: exporta a malha do corpo do robo para o Gazebo"
```

---

### Task 3: Pacote `geraldo_description` — URDF

**Files:**
- Create: `ros2_ws/src/geraldo_description/package.xml`, `ros2_ws/src/geraldo_description/CMakeLists.txt`, `ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`
- Create (vazias por ora): `ros2_ws/src/geraldo_description/launch/.gitkeep`, `ros2_ws/src/geraldo_description/config/.gitkeep`
- Test: `ros2_ws/src/geraldo_description/test/test_urdf.py`

**Interfaces:**
- Consumes: `meshes/geraldo_body.obj` (Tarefa 2) e `worlds/hospital.sdf` (gerado na Tarefa 4 do plano de fundação).
- Produces: robô `geraldo` com links `base_link`, `wheel_left_link`, `wheel_right_link`, `caster_link`, `lidar_link`; juntas `wheel_left_joint` e `wheel_right_joint` (contínuas, eixo `0 1 0`), `caster_joint`, `lidar_joint`; sensor `gpu_lidar` publicando `scan` (frame `lidar_link`); plugin `DiffDrive` em `/cmd_vel`, `/odom`, `/tf`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `ros2_ws/src/geraldo_description/test/test_urdf.py`:

```python
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

URDF = Path(__file__).resolve().parents[1] / "urdf" / "geraldo.urdf.xacro"


@pytest.fixture(scope="module")
def robot():
    out = subprocess.run(["xacro", str(URDF)], check=True, capture_output=True, text=True).stdout
    return ET.fromstring(out)


def joints(robot):
    return {j.get("name"): j for j in robot.findall("joint")}


def xyz(el):
    return [float(v) for v in el.find("origin").get("xyz").split()]


def test_links_and_joints_exist(robot):
    assert {l.get("name") for l in robot.findall("link")} == {
        "base_link", "wheel_left_link", "wheel_right_link", "caster_link", "lidar_link",
    }
    assert set(joints(robot)) == {"wheel_left_joint", "wheel_right_joint", "caster_joint", "lidar_joint"}


def test_wheels_are_continuous_around_y(robot):
    for name in ("wheel_left_joint", "wheel_right_joint"):
        j = joints(robot)[name]
        assert j.get("type") == "continuous"
        assert j.find("axis").get("xyz").split() == ["0", "1", "0"]


def test_wheel_layout_matches_the_spec(robot):
    left, right = (xyz(joints(robot)[n]) for n in ("wheel_left_joint", "wheel_right_joint"))
    assert left == pytest.approx([0.10, 0.225, 0.10])
    assert right == pytest.approx([0.10, -0.225, 0.10])


def test_diff_drive_plugin_matches_the_joints(robot):
    plugin = next(
        p for g in robot.findall("gazebo") for p in g.findall("plugin") if p.get("filename") == "gz-sim-diff-drive-system"
    )
    separation = float(plugin.find("wheel_separation").text)
    radius = float(plugin.find("wheel_radius").text)
    left, right = (xyz(joints(robot)[n]) for n in ("wheel_left_joint", "wheel_right_joint"))
    assert separation == pytest.approx(left[1] - right[1])       # 0,45 m
    assert radius == pytest.approx(left[2])                      # roda apoiada no chão
    assert plugin.find("topic").text == "/cmd_vel"
    assert plugin.find("odom_topic").text == "/odom"
    assert plugin.find("frame_id").text == "odom"
    assert plugin.find("child_frame_id").text == "base_link"


def test_lidar_sensor_publishes_scan(robot):
    sensor = next(s for g in robot.findall("gazebo") if g.get("reference") == "lidar_link" for s in g.findall("sensor"))
    assert sensor.get("type") == "gpu_lidar"
    assert sensor.find("topic").text == "scan"
    assert sensor.find("gz_frame_id").text == "lidar_link"


def test_collision_footprint_is_70_by_50(robot):
    base = next(l for l in robot.findall("link") if l.get("name") == "base_link")
    sizes = [[float(v) for v in c.find("geometry/box").get("size").split()] for c in base.findall("collision")]
    assert [0.70, 0.50, 0.20] in sizes


def test_mesh_uri_points_to_the_package(robot):
    base = next(l for l in robot.findall("link") if l.get("name") == "base_link")
    assert base.find("visual/geometry/mesh").get("filename") == "package://geraldo_description/meshes/geraldo_body.obj"
```

- [ ] **Step 2: Rodar e ver falhar**

Run (dentro do container): `docker compose -f docker/compose.yml run --rm ros bash -lc "cd /ws/src/geraldo_description && python3 -m pytest test/test_urdf.py -q"`
Expected: FAIL (o xacro não existe).

- [ ] **Step 3: Escrever `package.xml` e `CMakeLists.txt`**

`ros2_ws/src/geraldo_description/package.xml`:

```xml
<?xml version="1.0"?>
<package format="3">
  <name>geraldo_description</name>
  <version>0.1.0</version>
  <description>URDF, malhas, mundo e launch da simulação do G.E.R.A.L.D.O.</description>
  <maintainer email="geraldo@example.com">Samuel</maintainer>
  <license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <exec_depend>robot_state_publisher</exec_depend>
  <exec_depend>xacro</exec_depend>
  <exec_depend>ros_gz_sim</exec_depend>
  <exec_depend>ros_gz_bridge</exec_depend>
  <test_depend>ament_cmake_pytest</test_depend>
  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

`ros2_ws/src/geraldo_description/CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.8)
project(geraldo_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf meshes launch config worlds
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_urdf test/test_urdf.py)
endif()

ament_package()
```

Crie também `launch/.gitkeep` e `config/.gitkeep` (o `install(DIRECTORY ...)` exige que as pastas existam).

- [ ] **Step 4: Escrever o URDF**

`ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`:

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="geraldo">

  <xacro:property name="body_mass" value="25.0"/>
  <xacro:property name="wheel_radius" value="0.10"/>
  <xacro:property name="wheel_width" value="0.04"/>
  <xacro:property name="wheel_mass" value="1.5"/>
  <xacro:property name="wheel_x" value="0.10"/>
  <xacro:property name="wheel_y" value="0.225"/>
  <xacro:property name="caster_radius" value="0.04"/>
  <xacro:property name="caster_x" value="-0.30"/>
  <xacro:property name="pi_2" value="1.5707963"/>

  <link name="base_link">
    <visual>
      <geometry>
        <mesh filename="package://geraldo_description/meshes/geraldo_body.obj"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0.145"/>
      <geometry><box size="0.70 0.50 0.20"/></geometry>
    </collision>
    <collision>
      <origin xyz="0 0 0.36"/>
      <geometry><box size="0.48 0.40 0.22"/></geometry>
    </collision>
    <inertial>
      <origin xyz="0 0 0.22"/>
      <mass value="${body_mass}"/>
      <inertia ixx="0.943" ixy="0" ixz="0" iyy="1.443" iyz="0" izz="1.542"/>
    </inertial>
  </link>

  <xacro:macro name="wheel" params="side y">
    <link name="wheel_${side}_link">
      <visual>
        <origin rpy="${pi_2} 0 0"/>
        <geometry><cylinder radius="${wheel_radius}" length="${wheel_width}"/></geometry>
        <material name="tire_${side}"><color rgba="0.03 0.03 0.035 1"/></material>
      </visual>
      <collision>
        <origin rpy="${pi_2} 0 0"/>
        <geometry><cylinder radius="${wheel_radius}" length="${wheel_width}"/></geometry>
      </collision>
      <inertial>
        <origin rpy="${pi_2} 0 0"/>
        <mass value="${wheel_mass}"/>
        <inertia ixx="0.00395" ixy="0" ixz="0" iyy="0.00395" iyz="0" izz="0.0075"/>
      </inertial>
    </link>
    <joint name="wheel_${side}_joint" type="continuous">
      <parent link="base_link"/>
      <child link="wheel_${side}_link"/>
      <origin xyz="${wheel_x} ${y} ${wheel_radius}"/>
      <axis xyz="0 1 0"/>
    </joint>
    <gazebo reference="wheel_${side}_link">
      <mu1>1.0</mu1>
      <mu2>1.0</mu2>
    </gazebo>
  </xacro:macro>

  <xacro:wheel side="left" y="${wheel_y}"/>
  <xacro:wheel side="right" y="${-wheel_y}"/>

  <link name="caster_link">
    <visual>
      <geometry><sphere radius="${caster_radius}"/></geometry>
      <material name="caster"><color rgba="0.05 0.05 0.06 1"/></material>
    </visual>
    <collision>
      <geometry><sphere radius="${caster_radius}"/></geometry>
    </collision>
    <inertial>
      <mass value="0.2"/>
      <inertia ixx="0.000128" ixy="0" ixz="0" iyy="0.000128" iyz="0" izz="0.000128"/>
    </inertial>
  </link>
  <joint name="caster_joint" type="fixed">
    <parent link="base_link"/>
    <child link="caster_link"/>
    <origin xyz="${caster_x} 0 ${caster_radius}"/>
  </joint>
  <gazebo reference="caster_link">
    <mu1>0.0</mu1>
    <mu2>0.0</mu2>
  </gazebo>

  <link name="lidar_link">
    <inertial>
      <mass value="0.1"/>
      <inertia ixx="0.00003" ixy="0" ixz="0" iyy="0.00003" iyz="0" izz="0.00004"/>
    </inertial>
  </link>
  <joint name="lidar_joint" type="fixed">
    <parent link="base_link"/>
    <child link="lidar_link"/>
    <origin xyz="0.275 0 0.259"/>
  </joint>

  <!-- O baú bloqueia a visão para trás do LiDAR (fica 3,5 cm atrás dele): o campo de visão simulado é de ~172 graus.
       A traseira é coberta pelos sensores de alcance a 135 graus (semana 2). -->
  <gazebo reference="lidar_link">
    <sensor name="lidar" type="gpu_lidar">
      <pose>0 0 0 0 0 0</pose>
      <topic>scan</topic>
      <gz_frame_id>lidar_link</gz_frame_id>
      <update_rate>10</update_rate>
      <always_on>true</always_on>
      <visualize>false</visualize>
      <lidar>
        <scan>
          <horizontal>
            <samples>360</samples>
            <resolution>1</resolution>
            <min_angle>-1.5</min_angle>
            <max_angle>1.5</max_angle>
          </horizontal>
        </scan>
        <range>
          <min>0.12</min>
          <max>12.0</max>
          <resolution>0.01</resolution>
        </range>
        <noise>
          <type>gaussian</type>
          <mean>0.0</mean>
          <stddev>0.01</stddev>
        </noise>
      </lidar>
    </sensor>
  </gazebo>

  <gazebo>
    <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
      <left_joint>wheel_left_joint</left_joint>
      <right_joint>wheel_right_joint</right_joint>
      <wheel_separation>0.45</wheel_separation>
      <wheel_radius>0.10</wheel_radius>
      <odom_publish_frequency>30</odom_publish_frequency>
      <topic>/cmd_vel</topic>
      <odom_topic>/odom</odom_topic>
      <tf_topic>/tf</tf_topic>
      <frame_id>odom</frame_id>
      <child_frame_id>base_link</child_frame_id>
      <max_linear_velocity>0.8</max_linear_velocity>
      <max_angular_velocity>1.5</max_angular_velocity>
    </plugin>
  </gazebo>
</robot>
```

- [ ] **Step 5: Rodar e ver passar**

Run: `docker compose -f docker/compose.yml run --rm ros bash -lc "cd /ws/src/geraldo_description && python3 -m pytest test/test_urdf.py -q && xacro urdf/geraldo.urdf.xacro > /tmp/g.urdf && check_urdf /tmp/g.urdf | head -20"`
Expected: `7 passed` e `check_urdf` listando a árvore `base_link` com 4 filhos (`wheel_left_link`, `wheel_right_link`, `caster_link`, `lidar_link`).

- [ ] **Step 6: Commit**

```bash
git add ros2_ws/src/geraldo_description
git commit -m "feat: URDF do robo (rodas, rodizio, LiDAR e DiffDrive)"
```

---

### Task 4: Gazebo com o hospital, ponte e launch

**Files:**
- Create: `ros2_ws/src/geraldo_description/config/bridge.yaml`, `ros2_ws/src/geraldo_description/launch/sim.launch.py`
- Create: `ros2_ws/src/geraldo_description/test/smoke_sim.sh`
- Test: `ros2_ws/src/geraldo_description/test/test_launch_files.py`

**Interfaces:**
- Consumes: URDF (Tarefa 3), `worlds/hospital.sdf` (gerado).
- Produces: `ros2 launch geraldo_description sim.launch.py headless:=true x:=6.5 y:=26.5 yaw:=-1.5708`; tópicos ROS `/clock`, `/cmd_vel` (entrada), `/odom`, `/tf`, `/scan`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Create `ros2_ws/src/geraldo_description/test/test_launch_files.py`:

```python
import ast
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]


def test_bridge_has_the_contract_topics():
    entries = yaml.safe_load((PKG / "config/bridge.yaml").read_text())
    by_topic = {e["ros_topic_name"]: e for e in entries}
    assert set(by_topic) == {"/clock", "/cmd_vel", "/odom", "/tf", "/scan"}
    assert by_topic["/cmd_vel"]["direction"] == "ROS_TO_GZ"
    assert by_topic["/cmd_vel"]["ros_type_name"] == "geometry_msgs/msg/Twist"
    assert by_topic["/scan"]["ros_type_name"] == "sensor_msgs/msg/LaserScan"
    assert by_topic["/tf"]["ros_type_name"] == "tf2_msgs/msg/TFMessage"


def test_launch_file_is_valid_python_and_declares_the_arguments():
    src = (PKG / "launch/sim.launch.py").read_text()
    ast.parse(src)
    for arg in ("headless", "x", "y", "yaw"):
        assert f'DeclareLaunchArgument("{arg}"' in src
    assert "generate_launch_description" in src
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose -f docker/compose.yml run --rm ros bash -lc "cd /ws/src/geraldo_description && python3 -m pytest test/test_launch_files.py -q"`
Expected: FAIL (arquivos não existem).

- [ ] **Step 3: Escrever `config/bridge.yaml`**

```yaml
- ros_topic_name: /clock
  gz_topic_name: /clock
  ros_type_name: rosgraph_msgs/msg/Clock
  gz_type_name: gz.msgs.Clock
  direction: GZ_TO_ROS

- ros_topic_name: /cmd_vel
  gz_topic_name: /cmd_vel
  ros_type_name: geometry_msgs/msg/Twist
  gz_type_name: gz.msgs.Twist
  direction: ROS_TO_GZ

- ros_topic_name: /odom
  gz_topic_name: /odom
  ros_type_name: nav_msgs/msg/Odometry
  gz_type_name: gz.msgs.Odometry
  direction: GZ_TO_ROS

- ros_topic_name: /tf
  gz_topic_name: /tf
  ros_type_name: tf2_msgs/msg/TFMessage
  gz_type_name: gz.msgs.Pose_V
  direction: GZ_TO_ROS

- ros_topic_name: /scan
  gz_topic_name: /scan
  ros_type_name: sensor_msgs/msg/LaserScan
  gz_type_name: gz.msgs.LaserScan
  direction: GZ_TO_ROS
```

- [ ] **Step 4: Escrever `launch/sim.launch.py`**

```python
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
```

- [ ] **Step 5: Escrever o teste de fumaça da simulação**

`ros2_ws/src/geraldo_description/test/smoke_sim.sh`:

```bash
#!/usr/bin/env bash
# Sobe a simulação sem tela, confere /scan e /odom e anda 3 segundos com /cmd_vel.
set -euo pipefail

ros2 launch geraldo_description sim.launch.py headless:=true > /tmp/sim.log 2>&1 &
LAUNCH_PID=$!
trap 'kill $LAUNCH_PID 2>/dev/null || true' EXIT

timeout 120 bash -c 'until ros2 topic list | grep -q "^/scan$"; do sleep 2; done'
timeout 30 ros2 topic echo --once /scan --field ranges > /dev/null
timeout 30 ros2 topic echo --once /odom --field pose.pose.position > /tmp/odom0.txt

ros2 topic pub -t 30 -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}" > /dev/null
timeout 30 ros2 topic echo --once /odom --field pose.pose.position > /tmp/odom1.txt

if diff -q /tmp/odom0.txt /tmp/odom1.txt > /dev/null; then
  echo "SMOKE FALHOU: o robô não se mexeu"; exit 1
fi
echo "SMOKE OK"
```

- [ ] **Step 6: Rodar os testes de arquivo e ver passar**

Run: `docker compose -f docker/compose.yml run --rm ros bash -lc "cd /ws/src/geraldo_description && python3 -m pytest test/ -q"`
Expected: `9 passed`.

- [ ] **Step 7: Compilar e rodar o teste de fumaça**

```bash
docker compose -f docker/compose.yml run --rm ros bash -lc \
  "cd /ws && colcon build --symlink-install --packages-select geraldo_description && source install/setup.bash && bash src/geraldo_description/test/smoke_sim.sh"
```

Expected: termina com `SMOKE OK`. Se falhar, `docker compose ... run --rm ros cat /tmp/sim.log` mostra o motivo. Causas conhecidas e onde mexer:
- `package://geraldo_description/...` não resolve → confira `GZ_SIM_RESOURCE_PATH` no `sim.launch.py`.
- `/scan` não aparece → o LiDAR precisa de renderização; confira `--headless-rendering` e, no mundo, o plugin `gz-sim-sensors-system` (já gerado por `gen_hospital.py`).
- Robô cai ou atravessa o chão → confira o `<pose>` do `ground` no mundo e o `-z 0.02` do `create`.

- [ ] **Step 8: Commit**

```bash
git add ros2_ws/src/geraldo_description
git commit -m "feat: simulacao no Gazebo com o hospital, ponte ROS e launch"
```

---

### Task 5: Nav2 básico no hospital

**Files:**
- Create: `ros2_ws/src/geraldo_nav/package.xml`, `ros2_ws/src/geraldo_nav/CMakeLists.txt`, `ros2_ws/src/geraldo_nav/launch/nav.launch.py`
- Create: `tools/make_nav2_params.py`
- Create (gerado): `ros2_ws/src/geraldo_nav/config/nav2_params.yaml`
- Test: `tools/tests/test_make_nav2_params.py`

**Interfaces:**
- Consumes: `maps/hospital.yaml` e `config/waypoints.yaml` (gerados na Tarefa 4 do plano de fundação, já dentro de `geraldo_nav`), simulação (Tarefa 4).
- Produces: `ros2 launch geraldo_nav nav.launch.py` (map_server, AMCL, planejador, controlador, `/navigate_to_pose`); função `tools.make_nav2_params.patch_params(params: dict) -> dict`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_make_nav2_params.py`:

```python
from tools.make_nav2_params import FOOTPRINT, INITIAL_POSE, patch_params


def fake_defaults():
    return {
        "amcl": {"ros__parameters": {"set_initial_pose": False, "base_frame_id": "base_footprint"}},
        "local_costmap": {"local_costmap": {"ros__parameters": {"robot_radius": 0.22, "plugins": ["voxel_layer"]}}},
        "global_costmap": {"global_costmap": {"ros__parameters": {"robot_radius": 0.22}}},
    }


def test_costmaps_use_the_70_by_50_footprint_and_drop_robot_radius():
    out = patch_params(fake_defaults())
    for name in ("local_costmap", "global_costmap"):
        p = out[name][name]["ros__parameters"]
        assert p["footprint"] == FOOTPRINT
        assert "robot_radius" not in p
    assert FOOTPRINT == "[[0.35, 0.25], [0.35, -0.25], [-0.35, -0.25], [-0.35, 0.25]]"


def test_amcl_starts_at_the_robot_base_and_uses_base_link():
    p = patch_params(fake_defaults())["amcl"]["ros__parameters"]
    assert p["set_initial_pose"] is True
    assert p["initial_pose"] == INITIAL_POSE == {"x": 6.5, "y": 26.5, "z": 0.0, "yaw": -1.5708}
    assert p["base_frame_id"] == "base_link"


def test_other_parameters_are_preserved():
    out = patch_params(fake_defaults())
    assert out["local_costmap"]["local_costmap"]["ros__parameters"]["plugins"] == ["voxel_layer"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_make_nav2_params.py -q`
Expected: FAIL (`tools.make_nav2_params` não existe).

- [ ] **Step 3: Implementar o gerador de parâmetros**

Create `tools/make_nav2_params.py`:

```python
"""Gera ros2_ws/src/geraldo_nav/config/nav2_params.yaml a partir do padrão do nav2_bringup.

Uso (dentro do container): python3 tools/make_nav2_params.py
Ajusta o footprint (0,70 x 0,50 m) e a pose inicial do AMCL (base do robô, na farmácia).
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = Path("/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml")
OUT = ROOT / "ros2_ws/src/geraldo_nav/config/nav2_params.yaml"

FOOTPRINT = "[[0.35, 0.25], [0.35, -0.25], [-0.35, -0.25], [-0.35, 0.25]]"
INITIAL_POSE = {"x": 6.5, "y": 26.5, "z": 0.0, "yaw": -1.5708}


def patch_params(params: dict) -> dict:
    for name in ("local_costmap", "global_costmap"):
        p = params[name][name]["ros__parameters"]
        p.pop("robot_radius", None)
        p["footprint"] = FOOTPRINT
    amcl = params["amcl"]["ros__parameters"]
    amcl["set_initial_pose"] = True
    amcl["initial_pose"] = dict(INITIAL_POSE)
    amcl["base_frame_id"] = "base_link"
    return params


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULTS
    params = patch_params(yaml.safe_load(src.read_text()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(params, sort_keys=False))
    print(f"gerado: {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3b: Rodar e ver passar**

Run: `python -m pytest tools/tests/test_make_nav2_params.py -q`
Expected: `3 passed`.

- [ ] **Step 4: Criar o pacote `geraldo_nav` e o launch**

`ros2_ws/src/geraldo_nav/package.xml`:

```xml
<?xml version="1.0"?>
<package format="3">
  <name>geraldo_nav</name>
  <version>0.1.0</version>
  <description>Mapa, waypoints e launch do Nav2 do G.E.R.A.L.D.O.</description>
  <maintainer email="geraldo@example.com">Samuel</maintainer>
  <license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <exec_depend>nav2_bringup</exec_depend>
  <exec_depend>geraldo_description</exec_depend>
  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

`ros2_ws/src/geraldo_nav/CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.8)
project(geraldo_nav)

find_package(ament_cmake REQUIRED)

install(DIRECTORY maps config launch
  DESTINATION share/${PROJECT_NAME})

ament_package()
```

`ros2_ws/src/geraldo_nav/launch/nav.launch.py`:

```python
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
```

- [ ] **Step 5: Gerar os parâmetros, compilar e navegar**

O gerador roda **no host** (ele grava em `ros2_ws/src/geraldo_nav/config/`), usando o arquivo padrão copiado do container:

```bash
docker compose -f docker/compose.yml run --rm -T ros cat /opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml > /tmp/nav2_default.yaml
python tools/make_nav2_params.py /tmp/nav2_default.yaml
ls ros2_ws/src/geraldo_nav/config/
docker compose -f docker/compose.yml run --rm ros bash -lc "cd /ws && colcon build --symlink-install && echo BUILD_OK"
```

Expected: `nav2_params.yaml` e `waypoints.yaml` em `config/`, e `BUILD_OK`.

Depois, em **três terminais** dentro do container (abra cada um com `docker compose -f docker/compose.yml run --rm ros bash`, ou use `tmux`):

```bash
# terminal 1
source /ws/install/setup.bash && ros2 launch geraldo_description sim.launch.py headless:=true
# terminal 2
source /ws/install/setup.bash && ros2 launch geraldo_nav nav.launch.py
# terminal 3: meta em frente ao balcão da farmácia (waypoint farmacia_balcao: x=7, y=24)
source /ws/install/setup.bash && ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 7.0, y: 24.0, z: 0.0}, orientation: {z: -0.7071, w: 0.7071}}}}"
```

Expected: o terminal 3 termina com `Goal finished with status: SUCCEEDED`. Em seguida, uma meta longa: `x: 29.0, y: 25.0` (centro cirúrgico) deve ser `SUCCEEDED` pelo corredor norte.
Se o AMCL não localizar: confira que `/scan` e `/tf` chegam (`ros2 topic hz /scan`) e que a pose inicial do `nav2_params.yaml` é (6,5; 26,5; −1,5708), igual ao spawn.

- [ ] **Step 6: Commit**

```bash
git add tools/make_nav2_params.py tools/tests/test_make_nav2_params.py ros2_ws/src/geraldo_nav
git commit -m "feat: Nav2 basico no hospital (mapa, footprint 70x50 e launch)"
git push
```

Marco M1 (qua 11/11) fica a um passo: o `geraldo_dispatcher` (semana 2) liga a API a esta ação `NavigateToPose`.
