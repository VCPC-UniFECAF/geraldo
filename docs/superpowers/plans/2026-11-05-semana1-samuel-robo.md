# G.E.R.A.L.D.O. — Semana 1 (Samuel): robô e simulação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ter o robô simulado no Gazebo, dentro do hospital gerado do `hospital.yaml`, respondendo a `/cmd_vel`, publicando `/scan` e `/odom`, navegando com o Nav2 até os 10 pontos de parada e consumindo a fila do backend por um `geraldo_dispatcher` mínimo.

**Architecture:** Ambiente **nativo** na máquina do Samuel (Pop!_OS 24.04 com ROS 2 Jazzy e Gazebo Harmonic já instalados; a demo roda nela). O Docker fica como tarefa opcional da semana 2, para quem precisar rodar o robô em outra máquina. O pacote `geraldo_description` tem o URDF (xacro), a malha exportada do Blender, o mundo gerado e o launch do Gazebo com a ponte ROS↔Gazebo. O pacote `geraldo_nav` tem o mapa gerado, os waypoints e o launch do Nav2, com parâmetros gerados por script a partir do padrão do `nav2_bringup`. O pacote `geraldo_dispatcher` liga a API ao Nav2.

**Tech Stack:** ROS 2 Jazzy, Gazebo Harmonic 8.15 (`gz sim`), `ros_gz_sim`, `ros_gz_bridge`, Nav2 (`nav2_simple_commander`), xacro, Python (`urllib`, PyYAML, pytest), Blender (só para exportar a malha).

**Spec:** `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` (seções 4.1 e 8)

**Pré-requisito:** Tarefa 4 do plano `2026-11-05-semana1-samuel-fundacao.md` (`robot/hospital/hospital.yaml` e `robot/hospital/gen_hospital.py` com o hospital gerado). Nesta branch ela é executada **antes** das tarefas abaixo.

## Global Constraints

- Versões: ROS 2 **Jazzy** + Gazebo **Harmonic** (confirmar com a disciplina; se a disciplina usar outra, só os nomes `gz-sim-*` e os pacotes `ros-jazzy-*` mudam).
- Referencial `map → odom → base_link`; `base_link` no chão, frente = +X (spec §8).
- Rodas: separação de **0,45 m** (y = ±0,225), raio **0,10 m**, eixo Y; eixo das rodas em x = **+0,10 m**. Rodízio traseiro de raio 0,04 m em x = −0,30 m (spec §8).
- Footprint do Nav2: retângulo **0,70 × 0,50 m** com 10 cm de inflação (spec §4.1).
- Tópicos e estados: `docs/contracts/ros-interfaces.md`. Nenhum tópico novo sem PR no contrato.
- Mundo, mapa e waypoints são **gerados** por `robot/hospital/gen_hospital.py`; não editar à mão.
- O Gazebo **não usa o `.blend`**: usa a malha visual exportada e colisão simples (spec §8).
- Gazebo sem interface (`headless`) para desenvolver; a demo roda na máquina Linux do líder (spec §7).
- **Decisões do debate de 08/11/2026:** (D1) ambiente nativo, não Docker; (D2) `geraldo_dispatcher` mínimo entra na semana 1 (login, `next-task`, `NavigateToPose` origem e depois destino; sem `/robot/events`), testado contra uma API falsa que segue o contrato; (D3) LiDAR mantido em ~172° (o baú bloqueia a traseira), com a traseira coberta pelos sensores de proximidade na semana 2; (D4) portas de 1,0 m mantidas: parâmetros padrão do Nav2, inflação ajustada só se preciso, e um script que envia metas aos 10 pontos de parada.
- Comandos ROS rodam com `source /opt/ros/jazzy/setup.bash`. Saídas do colcon (`robot/ros2_ws/build`, `install`, `log`) não vão para o Git.
- Padrões (`docs/padroes-de-projeto.md`): o `geraldo_dispatcher` separa as responsabilidades em `ports.py` (interfaces `BackendPort` e `Navigator`), `api.py` (cliente HTTP), `waypoints.py` (poses), `dispatcher.py` (regra) e `node.py` (cola com o ROS). O `Dispatcher` recebe tudo pelo construtor (DIP); o Nav2 fica atrás de um **Adapter** (`Nav2Navigator`) e os testes usam um `FakeNavigator`. As ferramentas em `tools/` são funções puras com `main()` fino.
- Sem segredos no repositório.

---

### Task 1: Ambiente nativo conferido por script

**Files:**
- Create: `robot/scripts/check_ros_env.sh`, `robot/ros2_ws/.gitignore`
- Test: `robot/scripts/tests/test_check_ros_env.py`

**Interfaces:**
- Produces: `bash robot/scripts/check_ros_env.sh` (sai com 0 e imprime `AMBIENTE OK` quando tudo o que a simulação precisa está instalado; senão lista o que falta e o comando para instalar).

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `robot/scripts/tests/test_check_ros_env.py`:

```python
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(not os.path.exists("/opt/ros/jazzy/setup.bash"), reason="ROS 2 Jazzy não instalado")
def test_native_environment_has_everything_the_simulation_needs():
    result = subprocess.run(["bash", str(ROOT / "robot/scripts/check_ros_env.sh")], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout
    assert "AMBIENTE OK" in result.stdout
    for needed in ("nav2_bringup", "ros_gz_sim", "ros_gz_bridge", "xacro", "diff-drive"):
        assert needed in result.stdout, needed
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest robot/scripts/tests/test_check_ros_env.py -q`
Expected: FAIL (o script não existe).

- [ ] **Step 3: Escrever o script e o `.gitignore` do workspace**

Create `robot/scripts/check_ros_env.sh`:

```bash
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
```

Create `robot/ros2_ws/.gitignore`:

```gitignore
build/
install/
log/
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest robot/scripts/tests/test_check_ros_env.py -q`
Expected: `1 passed`. Se falhar com `FALTA nav2_...`, rode o `sudo apt install` que o próprio script imprime e repita.

- [ ] **Step 5: Commit**

```bash
git add robot/scripts/check_ros_env.sh robot/scripts/tests/test_check_ros_env.py robot/ros2_ws/.gitignore
git commit -m "feat: confere o ambiente nativo de ROS 2 + Gazebo + Nav2"
```

> **Docker (opcional, semana 2):** se o Pedro ou o Erik precisarem rodar o robô no CI ou na máquina deles, a imagem `osrf/ros:jazzy-desktop-full` com `ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup`, `ros-jazzy-ros-gz` e `ros-jazzy-xacro` cobre o mesmo ambiente. Não faz parte da semana 1.

---

### Task 2: Malha do robô exportada do Blender

**Files:**
- Create: `robot/scripts/export_blender_mesh.py`
- Create (gerados): `robot/ros2_ws/src/geraldo_description/meshes/geraldo_body.obj`, `robot/ros2_ws/src/geraldo_description/meshes/geraldo_body.mtl`
- Test: `robot/scripts/tests/test_export_mesh.py`

**Interfaces:**
- Consumes: `modelos-3d/geraldoV1.blend` (coleção `GERALDO`; objetos de roda começam com `roda_`, `disco_`, `tampa_`, rodízio com `rodizio_`).
- Produces: `meshes/geraldo_body.obj` — chassi, baú, sensores e LiDAR em metros, frente = +X, Z para cima, origem em `base_link` (as rodas e o rodízio **não** entram: viram primitivas no URDF).

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `robot/scripts/tests/test_export_mesh.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
OBJ = ROOT / "robot/ros2_ws/src/geraldo_description/meshes/geraldo_body.obj"


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender não instalado")
def test_export_creates_the_body_mesh_in_the_right_frame():
    subprocess.run(
        ["blender", "-b", str(ROOT / "modelos-3d/geraldoV1.blend"), "--python", str(ROOT / "robot/scripts/export_blender_mesh.py")],
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

Run: `python -m pytest robot/scripts/tests/test_export_mesh.py -q`
Expected: FAIL (`export_blender_mesh.py` não existe) ou `skipped` se não houver Blender na máquina; nesse caso peça ao Samuel para rodar.

- [ ] **Step 3: Implementar o script de exportação**

Create `robot/scripts/export_blender_mesh.py`:

```python
"""Exporta a malha do corpo do G.E.R.A.L.D.O. para o Gazebo (OBJ).

Uso: blender -b modelos-3d/geraldoV1.blend --python robot/scripts/export_blender_mesh.py
Rodas e rodízio ficam de fora: o URDF as descreve com primitivas para poderem girar.
"""
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "robot", "ros2_ws", "src", "geraldo_description", "meshes")
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

Run: `python -m pytest robot/scripts/tests/test_export_mesh.py -q`
Expected: `1 passed`. Confira o tamanho: `ls -la robot/ros2_ws/src/geraldo_description/meshes/` (cerca de 1–3 MB).

- [ ] **Step 5: Commit**

```bash
git add robot/scripts/export_blender_mesh.py robot/scripts/tests/test_export_mesh.py robot/ros2_ws/src/geraldo_description/meshes
git commit -m "feat: exporta a malha do corpo do robo para o Gazebo"
```

---

### Task 3: Pacote `geraldo_description` — URDF

**Files:**
- Create: `robot/ros2_ws/src/geraldo_description/package.xml`, `robot/ros2_ws/src/geraldo_description/CMakeLists.txt`, `robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`
- Create (vazias por ora): `robot/ros2_ws/src/geraldo_description/launch/.gitkeep`, `robot/ros2_ws/src/geraldo_description/config/.gitkeep`
- Test: `robot/ros2_ws/src/geraldo_description/test/test_urdf.py`

**Interfaces:**
- Consumes: `meshes/geraldo_body.obj` (Tarefa 2) e `worlds/hospital.sdf` (gerado na Tarefa 4 do plano de fundação).
- Produces: robô `geraldo` com links `base_link`, `wheel_left_link`, `wheel_right_link`, `caster_link`, `lidar_link`; juntas `wheel_left_joint` e `wheel_right_joint` (contínuas, eixo `0 1 0`), `caster_joint`, `lidar_joint`; sensor `gpu_lidar` publicando `scan` (frame `lidar_link`); plugin `DiffDrive` em `/cmd_vel`, `/odom`, `/tf`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `robot/ros2_ws/src/geraldo_description/test/test_urdf.py`:

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

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test/test_urdf.py -q)`
Expected: FAIL (o xacro não existe).

- [ ] **Step 3: Escrever `package.xml` e `CMakeLists.txt`**

`robot/ros2_ws/src/geraldo_description/package.xml`:

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

`robot/ros2_ws/src/geraldo_description/CMakeLists.txt`:

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

`robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`:

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

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test/test_urdf.py -q && xacro urdf/geraldo.urdf.xacro > /tmp/g.urdf && check_urdf /tmp/g.urdf | head -20)`
Expected: `7 passed` e `check_urdf` listando a árvore `base_link` com 4 filhos (`wheel_left_link`, `wheel_right_link`, `caster_link`, `lidar_link`).

- [ ] **Step 6: Commit**

```bash
git add robot/ros2_ws/src/geraldo_description
git commit -m "feat: URDF do robo (rodas, rodizio, LiDAR e DiffDrive)"
```

---

### Task 4: Gazebo com o hospital, ponte e launch

**Files:**
- Create: `robot/ros2_ws/src/geraldo_description/config/bridge.yaml`, `robot/ros2_ws/src/geraldo_description/launch/sim.launch.py`
- Create: `robot/ros2_ws/src/geraldo_description/test/smoke_sim.sh`
- Test: `robot/ros2_ws/src/geraldo_description/test/test_launch_files.py`

**Interfaces:**
- Consumes: URDF (Tarefa 3), `worlds/hospital.sdf` (gerado).
- Produces: `ros2 launch geraldo_description sim.launch.py headless:=true x:=6.5 y:=26.5 yaw:=-1.5708`; tópicos ROS `/clock`, `/cmd_vel` (entrada), `/odom`, `/tf`, `/scan`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Create `robot/ros2_ws/src/geraldo_description/test/test_launch_files.py`:

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

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test/test_launch_files.py -q)`
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

`robot/ros2_ws/src/geraldo_description/test/smoke_sim.sh`:

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

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test/ -q)`
Expected: `9 passed`.

- [ ] **Step 7: Compilar e rodar o teste de fumaça**

```bash
source /opt/ros/jazzy/setup.bash
cd robot/ros2_ws && colcon build --symlink-install --packages-select geraldo_description && source install/setup.bash && bash src/geraldo_description/test/smoke_sim.sh
```

Expected: termina com `SMOKE OK`. Se falhar, `cat /tmp/sim.log` mostra o motivo. Causas conhecidas e onde mexer:
- GPU híbrida (Intel + NVIDIA) lenta ou LiDAR sem renderizar → rode com `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia`; com tela sob Wayland, use `QT_QPA_PLATFORM=xcb`.
- `package://geraldo_description/...` não resolve → confira `GZ_SIM_RESOURCE_PATH` no `sim.launch.py`.
- `/scan` não aparece → o LiDAR precisa de renderização; confira `--headless-rendering` e, no mundo, o plugin `gz-sim-sensors-system` (já gerado por `gen_hospital.py`).
- Robô cai ou atravessa o chão → confira o `<pose>` do `ground` no mundo e o `-z 0.02` do `create`.

- [ ] **Step 8: Commit**

```bash
git add robot/ros2_ws/src/geraldo_description
git commit -m "feat: simulacao no Gazebo com o hospital, ponte ROS e launch"
```

---

### Task 5: Nav2 básico no hospital

**Files:**
- Create: `robot/ros2_ws/src/geraldo_nav/package.xml`, `robot/ros2_ws/src/geraldo_nav/CMakeLists.txt`, `robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py`
- Create: `robot/scripts/make_nav2_params.py`
- Create (gerado): `robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml`
- Test: `robot/scripts/tests/test_make_nav2_params.py`

**Interfaces:**
- Consumes: `maps/hospital.yaml` e `config/waypoints.yaml` (gerados na Tarefa 4 do plano de fundação, já dentro de `geraldo_nav`), simulação (Tarefa 4).
- Produces: `ros2 launch geraldo_nav nav.launch.py` (map_server, AMCL, planejador, controlador, `/navigate_to_pose`); função `robot.scripts.make_nav2_params.patch_params(params: dict) -> dict`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `robot/scripts/tests/test_make_nav2_params.py`:

```python
from robot.scripts.make_nav2_params import FOOTPRINT, INITIAL_POSE, patch_params


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

Run: `python -m pytest robot/scripts/tests/test_make_nav2_params.py -q`
Expected: FAIL (`robot.scripts.make_nav2_params` não existe).

- [ ] **Step 3: Implementar o gerador de parâmetros**

Create `robot/scripts/make_nav2_params.py`:

```python
"""Gera robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml a partir do padrão do nav2_bringup.

Uso: python3 robot/scripts/make_nav2_params.py
Ajusta o footprint (0,70 x 0,50 m) e a pose inicial do AMCL (base do robô, na farmácia).
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = Path("/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml")
OUT = ROOT / "robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml"

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

Run: `python -m pytest robot/scripts/tests/test_make_nav2_params.py -q`
Expected: `3 passed`.

- [ ] **Step 4: Criar o pacote `geraldo_nav` e o launch**

`robot/ros2_ws/src/geraldo_nav/package.xml`:

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

`robot/ros2_ws/src/geraldo_nav/CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.8)
project(geraldo_nav)

find_package(ament_cmake REQUIRED)

install(DIRECTORY maps config launch
  DESTINATION share/${PROJECT_NAME})

ament_package()
```

`robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py`:

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

```bash
source /opt/ros/jazzy/setup.bash
python robot/scripts/make_nav2_params.py
ls robot/ros2_ws/src/geraldo_nav/config/
cd robot/ros2_ws && colcon build --symlink-install && echo BUILD_OK
```

Expected: `nav2_params.yaml` e `waypoints.yaml` em `config/`, e `BUILD_OK`.

Depois, em **três terminais** (todos com `source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash`):

```bash
# terminal 1
ros2 launch geraldo_description sim.launch.py headless:=true
# terminal 2
ros2 launch geraldo_nav nav.launch.py
# terminal 3: meta em frente ao balcão da farmácia (waypoint farmacia_balcao: x=7, y=24)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 7.0, y: 24.0, z: 0.0}, orientation: {z: -0.7071, w: 0.7071}}}}"
```

Expected: o terminal 3 termina com `Goal finished with status: SUCCEEDED`. Em seguida, uma meta longa: `x: 29.0, y: 25.0` (centro cirúrgico) deve ser `SUCCEEDED` pelo corredor norte.
Se o AMCL não localizar: confira que `/scan` e `/tf` chegam (`ros2 topic hz /scan`) e que a pose inicial do `nav2_params.yaml` é (6,5; 26,5; −1,5708), igual ao spawn.

- [ ] **Step 6: Commit**

```bash
git add robot/scripts/make_nav2_params.py robot/scripts/tests/test_make_nav2_params.py robot/ros2_ws/src/geraldo_nav
git commit -m "feat: Nav2 basico no hospital (mapa, footprint 70x50 e launch)"
```

As tarefas 6 e 7 fecham o marco M1 (qua 11/11): o teste dos pontos de parada valida as portas e o `geraldo_dispatcher` liga a API a esta ação `NavigateToPose`.

---

### Task 6: Teste dos 10 pontos de parada (valida as portas de 1,0 m)

**Files:**
- Create: `robot/scripts/nav_goal_sweep.py`
- Test: `robot/scripts/tests/test_nav_goal_sweep.py`

**Interfaces:**
- Consumes: `robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml` (gerado), simulação e Nav2 rodando (Tarefas 4 e 5).
- Produces: `robot.scripts.nav_goal_sweep.load_stops(path=WAYPOINTS) -> list[tuple[str, float, float, float]]` (id, x, y, yaw em radianos; todos os pontos exceto `base_robo`), `yaw_to_quaternion(yaw) -> tuple[float, float]` (z, w) e o comando `python3 robot/scripts/nav_goal_sweep.py [--timeout 180]`, que sai com 0 só se **todos** os pontos forem alcançados.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Create `robot/scripts/tests/test_nav_goal_sweep.py`:

```python
import math
from pathlib import Path

import pytest

from robot.scripts.nav_goal_sweep import WAYPOINTS, load_stops, yaw_to_quaternion


def write_waypoints(path: Path) -> Path:
    path.write_text(
        "waypoints:\n"
        "  base_robo: {room: farmacia, x: 6.5, y: 26.5, yaw: 270}\n"
        "  farmacia_balcao: {room: farmacia, x: 7, y: 24, yaw: 270}\n"
        "  cc_entrega: {room: centro_cirurgico, x: 29, y: 25, yaw: 90}\n",
        encoding="utf-8",
    )
    return path


def test_load_stops_skips_the_robot_base_and_converts_degrees(tmp_path):
    stops = load_stops(write_waypoints(tmp_path / "w.yaml"))
    assert [s[0] for s in stops] == ["farmacia_balcao", "cc_entrega"]
    assert stops[0][1:3] == (7, 24)
    assert stops[1][3] == pytest.approx(math.pi / 2)


def test_yaw_to_quaternion():
    z, w = yaw_to_quaternion(0.0)
    assert (z, w) == (0.0, 1.0)
    z, w = yaw_to_quaternion(math.pi)
    assert z == pytest.approx(1.0) and w == pytest.approx(0.0, abs=1e-9)


@pytest.mark.skipif(not WAYPOINTS.exists(), reason="waypoints.yaml ainda não foi gerado")
def test_generated_waypoints_have_the_ten_stops():
    ids = {s[0] for s in load_stops()}
    assert ids == {
        "farmacia_balcao", "banco_sangue_retirada", "rouparia_coleta", "cc_entrega", "uti_entrega",
        "ps_entrega", "cons1_entrega", "cons2_entrega", "enf214_entrega", "enf215_entrega",
    }
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest robot/scripts/tests/test_nav_goal_sweep.py -q`
Expected: FAIL (`robot.scripts.nav_goal_sweep` não existe).

- [ ] **Step 3: Implementar**

Create `robot/scripts/nav_goal_sweep.py`:

```python
#!/usr/bin/env python3
"""Manda o robô a cada ponto de parada do hospital e confere se o Nav2 chega (valida as portas de 1,0 m).

Uso (com a simulação e o Nav2 rodando, ROS carregado):
  python3 robot/scripts/nav_goal_sweep.py [--timeout 180]
Sai com 0 só se todos os pontos forem alcançados.
"""
import argparse
import math
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WAYPOINTS = ROOT / "robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml"


def load_stops(path=WAYPOINTS) -> list[tuple[str, float, float, float]]:
    """(id, x, y, yaw em radianos) de todos os pontos, exceto a base do robô."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["waypoints"]
    return [(wid, w["x"], w["y"], math.radians(w["yaw"])) for wid, w in data.items() if wid != "base_robo"]


def yaw_to_quaternion(yaw: float) -> tuple[float, float]:
    """(z, w) do quaternion de uma rotação em torno de Z."""
    return math.sin(yaw / 2), math.cos(yaw / 2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=float, default=180.0, help="segundos por ponto")
    args = ap.parse_args()

    import rclpy
    from geometry_msgs.msg import PoseStamped
    from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

    rclpy.init()
    nav = BasicNavigator()
    nav.waitUntilNav2Active()
    failed = []
    for wid, x, y, yaw in load_stops():
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = nav.get_clock().now().to_msg()
        goal.pose.position.x, goal.pose.position.y = x, y
        goal.pose.orientation.z, goal.pose.orientation.w = yaw_to_quaternion(yaw)
        nav.goToPose(goal)
        start = time.monotonic()
        while not nav.isTaskComplete():
            if time.monotonic() - start > args.timeout:
                nav.cancelTask()
                break
            time.sleep(0.5)
        ok = nav.getResult() == TaskResult.SUCCEEDED
        print(f"{'ok    ' if ok else 'FALHOU'} {wid:24s} {time.monotonic() - start:5.0f}s")
        if not ok:
            failed.append(wid)
    rclpy.shutdown()
    print("TODOS OS PONTOS OK" if not failed else f"FALHARAM: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest robot/scripts/tests/test_nav_goal_sweep.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Rodar com a simulação (precisa dos terminais 1 e 2 da Tarefa 5)**

```bash
source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash
python3 robot/scripts/nav_goal_sweep.py
```

Expected: 10 linhas `ok` e `TODOS OS PONTOS OK`. Se alguma sala falhar, é quase sempre a porta: ajuste, nesta ordem, `inflation_radius` (de 0,55 para 0,35) e `cost_scaling_factor` (de 3,0 para 5,0) nos dois costmaps de `robot/scripts/make_nav2_params.py`, gere de novo e repita. Só se ainda falhar, avalie alargar `door_width` no `hospital.yaml` (plano B, exige avisar o grupo) ou trocar o controlador.

- [ ] **Step 6: Commit**

```bash
git add robot/scripts/nav_goal_sweep.py robot/scripts/tests/test_nav_goal_sweep.py robot/scripts/make_nav2_params.py
git commit -m "feat: teste dos 10 pontos de parada do hospital no Nav2"
```

---

### Task 7: `geraldo_dispatcher` mínimo e API falsa

**Files:**
- Create: `robot/scripts/fake_backend.py`
- Create: `robot/ros2_ws/src/geraldo_dispatcher/package.xml`, `setup.py`, `setup.cfg`, `resource/geraldo_dispatcher`
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/__init__.py`, `ports.py`, `api.py`, `waypoints.py`, `dispatcher.py`, `node.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py`

**Interfaces:**
- Consumes: contrato `POST /auth/login` e `POST /robot/next-task` (`RobotTask`: `id`, `origin_waypoint`, `dest_waypoint`...) e `waypoints.yaml` (Tarefa 4 do plano de fundação).
- Produces:
  - `robot.scripts.fake_backend.FakeBackend(tasks=None, username="robo", password="robo-local", port=0)` com `start() -> self`, `stop()`, `url`, `calls`, `expire_token()`; CLI `python robot/scripts/fake_backend.py --port 8000`.
  - `geraldo_dispatcher.ports.BackendPort` (`next_task() -> dict | None`) e `Navigator` (`go_to(pose) -> bool`): interfaces pequenas (ISP).
  - `geraldo_dispatcher.api.BackendClient(base_url, username, password)`, um `BackendPort` com `login()` e `next_task()` (só biblioteca padrão; refaz o login uma vez se o token expirar).
  - `geraldo_dispatcher.waypoints.Pose(x, y, yaw)` (`Pose.from_dict(d)` converte graus em radianos; `quaternion() -> (z, w)`) e `load_poses(path) -> dict[str, Pose]`.
  - `geraldo_dispatcher.node.Nav2Navigator(BasicNavigator, timeout)`, o adapter que implementa `Navigator`.
  - `geraldo_dispatcher.dispatcher.Dispatcher(backend, poses, navigator, log=print).run_once() -> dict | None`: `None` se a fila está vazia; senão a própria tarefa com o campo extra `result` (`"CHEGOU"` ou `"FALHOU"`; no segundo caso, também `failed_at`).
  - Executável: `ros2 run geraldo_dispatcher dispatcher` (variáveis `GERALDO_API_URL`, `GERALDO_ROBOT_PASSWORD`).

- [ ] **Step 1: Escrever a API falsa**

Create `robot/scripts/fake_backend.py`:

```python
#!/usr/bin/env python3
"""API falsa do robô para desenvolver o dispatcher sem o backend. Segue docs/contracts/openapi.yaml
(somente POST /auth/login e POST /robot/next-task).

Uso: python robot/scripts/fake_backend.py --port 8000     (usuário `robo`, senha `robo-local`)
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEMO_TASKS = [
    {"id": 1, "origin_id": "farmacia", "dest_id": "consultorio1", "items": [{"item_id": "dipirona-500mg", "quantity": 5}],
     "priority": "media", "status": "EM_ROTA", "requested_by": 1, "created_at": "2026-11-09T13:20:00Z",
     "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega"},
    {"id": 2, "origin_id": "banco_sangue", "dest_id": "centro_cirurgico", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}],
     "priority": "critica", "status": "EM_ROTA", "requested_by": 1, "created_at": "2026-11-09T13:25:00Z",
     "origin_waypoint": "banco_sangue_retirada", "dest_waypoint": "cc_entrega"},
]


class FakeBackend:
    def __init__(self, tasks=None, username="robo", password="robo-local", port=0) -> None:
        self.tasks = list(tasks or [])
        self.username, self.password = username, password
        self.token_number = 1
        self.calls: list[str] = []
        backend = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silencia o log do servidor
                pass

            def _send(self, code, body=None):
                payload = json.dumps(body).encode() if body is not None else b""
                self.send_response(code)
                if body is not None:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                backend.calls.append(self.path)
                if self.path == "/auth/login":
                    body = json.loads(raw)
                    if body.get("username") == backend.username and body.get("password") == backend.password:
                        return self._send(200, {"access_token": backend.token, "token_type": "bearer"})
                    return self._send(401, {"detail": "Usuário ou senha incorretos. Tente de novo."})
                if self.path == "/robot/next-task":
                    if self.headers.get("Authorization") != f"Bearer {backend.token}":
                        return self._send(401, {"detail": "Sessão inválida ou expirada. Entre de novo."})
                    return self._send(200, backend.tasks.pop(0)) if backend.tasks else self._send(204)
                return self._send(404, {"detail": "Não encontrado."})

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def token(self) -> str:
        return f"fake-token-{self.token_number}"

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def expire_token(self) -> None:
        self.token_number += 1

    def start(self) -> "FakeBackend":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    backend = FakeBackend(DEMO_TASKS, port=args.port).start()
    print(f"API falsa em {backend.url} (usuário robo, senha robo-local). Ctrl+C para sair.")
    threading.Event().wait()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Escrever os testes do dispatcher (falham primeiro)**

Create `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py`:

```python
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.api import BackendClient  # noqa: E402
from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
from geraldo_dispatcher.ports import BackendPort, Navigator  # noqa: E402
from geraldo_dispatcher.waypoints import Pose, load_poses  # noqa: E402
from robot.scripts.fake_backend import DEMO_TASKS, FakeBackend  # noqa: E402

POSES = {
    "farmacia_balcao": Pose(7, 24, math.radians(270)),
    "cons1_entrega": Pose(14.5, 4, math.radians(270)),
    "banco_sangue_retirada": Pose(17, 25, math.radians(90)),
    "cc_entrega": Pose(29, 25, math.radians(90)),
}


class FakeNavigator(Navigator):  # substituto de teste do Nav2 (LSP)
    def __init__(self, reaches: bool = True) -> None:
        self.visited: list[Pose] = []
        self._reaches = reaches

    def go_to(self, pose: Pose) -> bool:
        self.visited.append(pose)
        return self._reaches


class ListBackend(BackendPort):  # substituto de teste do backend: sem HTTP
    def __init__(self, tasks: list[dict]) -> None:
        self._tasks = tasks

    def next_task(self):
        return self._tasks.pop(0) if self._tasks else None


@pytest.fixture
def backend():
    server = FakeBackend([dict(t) for t in DEMO_TASKS]).start()
    yield server
    server.stop()


def client_for(backend, password="robo-local"):
    return BackendClient(backend.url, "robo", password)


def test_load_poses_converts_degrees_to_radians(tmp_path):
    path = tmp_path / "w.yaml"
    path.write_text("waypoints:\n  a: {room: x, x: 1.5, y: 2.5, yaw: 90}\n", encoding="utf-8")
    pose = load_poses(path)["a"]
    assert (pose.x, pose.y) == (1.5, 2.5)
    assert pose.yaw == pytest.approx(math.pi / 2)
    z, w = pose.quaternion()
    assert z == pytest.approx(math.sin(math.pi / 4)) and w == pytest.approx(math.cos(math.pi / 4))


def test_pose_from_dict_converts_degrees_to_radians():
    pose = Pose.from_dict({"x": 1.0, "y": 2.0, "yaw": 180})
    assert (pose.x, pose.y) == (1.0, 2.0) and pose.yaw == pytest.approx(math.pi)


def test_login_failure_has_a_clear_message(backend):
    with pytest.raises(RuntimeError, match="Login do robô falhou"):
        client_for(backend, "errada").login()


def test_next_task_returns_tasks_in_order_then_none(backend):
    client = client_for(backend)
    client.login()
    assert client.next_task()["id"] == 1
    assert client.next_task()["id"] == 2
    assert client.next_task() is None


def test_client_logs_in_again_when_the_token_expires(backend):
    client = client_for(backend)
    client.login()
    backend.expire_token()
    assert client.next_task()["id"] == 1
    assert backend.calls.count("/auth/login") == 2


def test_dispatcher_goes_to_origin_then_destination(backend):
    navigator = FakeNavigator()
    client = client_for(backend)
    client.login()
    result = Dispatcher(client, POSES, navigator, log=lambda *_: None).run_once()
    assert navigator.visited == [POSES["farmacia_balcao"], POSES["cons1_entrega"]]
    assert result["id"] == 1 and result["result"] == "CHEGOU"


def test_dispatcher_stops_when_the_robot_cannot_reach_the_origin(backend):
    navigator = FakeNavigator(reaches=False)
    client = client_for(backend)
    client.login()
    result = Dispatcher(client, POSES, navigator, log=lambda *_: None).run_once()
    assert result["result"] == "FALHOU" and result["failed_at"] == "farmacia_balcao"
    assert len(navigator.visited) == 1


def test_dispatcher_returns_none_on_an_empty_queue(backend):
    backend.tasks.clear()
    client = client_for(backend)
    client.login()
    assert Dispatcher(client, POSES, FakeNavigator(), log=lambda *_: None).run_once() is None


def test_unknown_waypoint_is_an_error_not_a_silent_skip(backend):
    client = client_for(backend)
    client.login()
    with pytest.raises(KeyError, match="farmacia_balcao"):
        Dispatcher(client, {}, FakeNavigator(), log=lambda *_: None).run_once()


def test_dispatcher_works_with_any_backend_port_without_http():
    task = {"id": 5, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cc_entrega"}
    navigator = FakeNavigator()
    result = Dispatcher(ListBackend([task]), POSES, navigator, log=lambda *_: None).run_once()
    assert result["result"] == "CHEGOU" and navigator.visited == [POSES["farmacia_balcao"], POSES["cc_entrega"]]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q)`
Expected: FAIL (o pacote não existe).

- [ ] **Step 4: Criar o pacote Python**

`robot/ros2_ws/src/geraldo_dispatcher/package.xml`:

```xml
<?xml version="1.0"?>
<package format="3">
  <name>geraldo_dispatcher</name>
  <version>0.1.0</version>
  <description>Liga a fila do backend ao Nav2: pega a próxima entrega e leva o robô da origem ao destino.</description>
  <maintainer email="geraldo@example.com">Samuel</maintainer>
  <license>MIT</license>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>geometry_msgs</exec_depend>
  <exec_depend>nav2_simple_commander</exec_depend>
  <exec_depend>geraldo_nav</exec_depend>
  <test_depend>python3-pytest</test_depend>
  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

`robot/ros2_ws/src/geraldo_dispatcher/setup.py`:

```python
from setuptools import find_packages, setup

package_name = "geraldo_dispatcher"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "pyyaml"],
    zip_safe=True,
    maintainer="Samuel",
    maintainer_email="geraldo@example.com",
    description="Dispatcher do G.E.R.A.L.D.O.",
    license="MIT",
    entry_points={"console_scripts": ["dispatcher = geraldo_dispatcher.node:main"]},
)
```

`robot/ros2_ws/src/geraldo_dispatcher/setup.cfg`:

```ini
[develop]
script_dir=$base/lib/geraldo_dispatcher
[install]
install_scripts=$base/lib/geraldo_dispatcher
```

Crie `resource/geraldo_dispatcher` (arquivo vazio) e `geraldo_dispatcher/__init__.py` (vazio).

`robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py`:

```python
from abc import ABC, abstractmethod

from .waypoints import Pose


class BackendPort(ABC):  # porta: tudo o que o dispatcher precisa do backend (ISP)
    @abstractmethod
    def next_task(self) -> dict | None:
        """Próxima entrega da fila, ou None se não há nenhuma."""


class Navigator(ABC):  # porta: tudo o que o dispatcher precisa da navegação
    @abstractmethod
    def go_to(self, pose: Pose) -> bool:
        """Leva o robô até a pose. True se chegou."""
```

`robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/api.py`:

```python
import json
import urllib.error
import urllib.request

from .ports import BackendPort


class BackendClient(BackendPort):  # ADAPTER: traduz a API HTTP do backend para a porta que o dispatcher usa
    """Cliente mínimo do backend (só biblioteca padrão): login do robô e próxima tarefa."""

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.username, self.password, self.timeout = username, password, timeout
        self._token: str | None = None

    def _post(self, path: str, body: dict | None = None):
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        data = json.dumps(body).encode() if body is not None else b""
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method="POST")
        return urllib.request.urlopen(request, timeout=self.timeout)

    def login(self) -> None:
        try:
            with self._post("/auth/login", {"username": self.username, "password": self.password}) as response:
                self._token = json.load(response)["access_token"]
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"Login do robô falhou ({err.code}). Confira usuário e senha.") from err

    def next_task(self) -> dict | None:
        try:
            return self._read_task()
        except urllib.error.HTTPError as err:
            if err.code != 401:
                raise
            self.login()  # o token expirou: entra de novo uma vez
            return self._read_task()

    def _read_task(self) -> dict | None:
        with self._post("/robot/next-task") as response:
            return None if response.status == 204 else json.load(response)
```

`robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/waypoints.py`:

```python
import math
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    yaw: float  # radianos

    @classmethod
    def from_dict(cls, data: dict) -> "Pose":  # FACTORY: o waypoints.yaml guarda o yaw em graus
        return cls(data["x"], data["y"], math.radians(data["yaw"]))

    def quaternion(self) -> tuple[float, float]:
        """(z, w) do quaternion de uma rotação em torno de Z."""
        return math.sin(self.yaw / 2), math.cos(self.yaw / 2)


def load_poses(path) -> dict[str, Pose]:
    """Lê o waypoints.yaml gerado por robot/hospital/gen_hospital.py (yaw em graus) e devolve poses em radianos."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["waypoints"]
    return {wid: Pose.from_dict(w) for wid, w in data.items()}
```

`robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/dispatcher.py`:

```python
from .ports import BackendPort, Navigator
from .waypoints import Pose


class Dispatcher:
    """Pega a próxima entrega da fila e leva o robô à origem e depois ao destino.

    Só conhece as portas `BackendPort` e `Navigator` (DIP): o Nav2 e o HTTP entram pelo construtor.
    """

    def __init__(self, backend: BackendPort, poses: dict[str, Pose], navigator: Navigator, log=print) -> None:
        self.backend, self.poses, self.navigator, self.log = backend, poses, navigator, log

    def run_once(self) -> dict | None:
        task = self.backend.next_task()
        if task is None:
            return None
        for key in ("origin_waypoint", "dest_waypoint"):
            waypoint = task[key]
            if waypoint not in self.poses:
                raise KeyError(f"Waypoint desconhecido: {waypoint}. Gere o hospital de novo (robot/hospital/gen_hospital.py).")
            self.log(f"entrega {task['id']}: indo para {waypoint}")
            if not self.navigator.go_to(self.poses[waypoint]):
                self.log(f"entrega {task['id']}: não chegou a {waypoint}")
                return {**task, "result": "FALHOU", "failed_at": waypoint}
        self.log(f"entrega {task['id']}: chegou ao destino")
        return {**task, "result": "CHEGOU"}
```

`robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`:

```python
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
```

- [ ] **Step 5: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q)`
Expected: `10 passed`.

- [ ] **Step 6: Compilar o pacote e conferir o executável**

```bash
source /opt/ros/jazzy/setup.bash
cd robot/ros2_ws && colcon build --symlink-install --packages-select geraldo_nav geraldo_dispatcher && source install/setup.bash
ros2 pkg executables geraldo_dispatcher
```

Expected: `geraldo_dispatcher dispatcher`.

- [ ] **Step 7: Rodar de ponta a ponta com a API falsa (simulação e Nav2 nos terminais 1 e 2 da Tarefa 5)**

```bash
# terminal 3
python robot/scripts/fake_backend.py --port 8000
# terminal 4
source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash
GERALDO_ROBOT_PASSWORD=robo-local ros2 run geraldo_dispatcher dispatcher
```

Expected: no terminal 4, `entrega 1: indo para farmacia_balcao`, depois `... cons1_entrega` e `entrega 1: chegou ao destino`, e o mesmo para a entrega 2; depois o robô fica esperando a fila. Com o backend do Erik rodando no lugar da API falsa (`GERALDO_API_URL=http://localhost:8000` e a senha do usuário `robo`), este é o M1 de verdade.

- [ ] **Step 8: Commit**

```bash
git add robot/scripts/fake_backend.py robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat: geraldo_dispatcher minimo (portas, adapter do Nav2 e API falsa)"
```
