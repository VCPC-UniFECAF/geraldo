import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1]
URDF = PKG / "urdf" / "geraldo.urdf.xacro"


@pytest.fixture(scope="module")
def robot():
    out = subprocess.run(["xacro", str(URDF)], check=True, capture_output=True, text=True).stdout
    return ET.fromstring(out)


def joints(robot):
    return {j.get("name"): j for j in robot.findall("joint")}


def link(robot, name):
    return next(l for l in robot.findall("link") if l.get("name") == name)


def xyz(el):
    return [float(v) for v in el.find("origin").get("xyz").split()]


RANGE = ("front_c", "front_l45", "front_r45", "rear_l135", "rear_r135")


def test_links_and_joints_exist(robot):
    assert {l.get("name") for l in robot.findall("link")} == {
        "base_link", "wheel_left_link", "wheel_right_link", "caster_swivel_link", "caster_wheel_link", "lidar_link",
        *(f"range_{n}_link" for n in RANGE),
    }
    assert set(joints(robot)) == {
        "wheel_left_joint", "wheel_right_joint", "caster_swivel_joint", "caster_wheel_joint", "lidar_joint",
        *(f"range_{n}_joint" for n in RANGE),
    }


def test_wheels_are_continuous_around_y(robot):
    for name in ("wheel_left_joint", "wheel_right_joint"):
        j = joints(robot)[name]
        assert j.get("type") == "continuous"
        assert j.find("axis").get("xyz").split() == ["0", "1", "0"]


def test_wheel_layout_matches_the_spec(robot):
    left, right = (xyz(joints(robot)[n]) for n in ("wheel_left_joint", "wheel_right_joint"))
    assert left == pytest.approx([0.10, 0.225, 0.10])
    assert right == pytest.approx([0.10, -0.225, 0.10])


def test_caster_swivels_around_z_and_its_wheel_rolls_around_y(robot):
    swivel, wheel = joints(robot)["caster_swivel_joint"], joints(robot)["caster_wheel_joint"]
    assert (swivel.get("type"), swivel.find("axis").get("xyz").split()) == ("continuous", ["0", "0", "1"])
    assert swivel.find("parent").get("link") == "base_link" and swivel.find("child").get("link") == "caster_swivel_link"
    assert xyz(swivel) == pytest.approx([-0.25, 0.0, 0.09])       # pino vertical do rodízio
    assert (wheel.get("type"), wheel.find("axis").get("xyz").split()) == ("continuous", ["0", "1", "0"])
    assert wheel.find("parent").get("link") == "caster_swivel_link" and wheel.find("child").get("link") == "caster_wheel_link"
    assert xyz(wheel) == pytest.approx([-0.015, 0.0, -0.05])      # a roda fica 1,5 cm atrás do pino (trail)


def test_caster_wheel_rests_on_the_floor(robot):
    height = xyz(joints(robot)["caster_swivel_joint"])[2] + xyz(joints(robot)["caster_wheel_joint"])[2]
    radius = float(link(robot, "caster_wheel_link").find("collision/geometry/cylinder").get("radius"))
    assert height == pytest.approx(radius)                       # centro da roda à altura do raio


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


def test_diff_drive_allows_the_nav2_cruise_speed_and_turn_rate(robot):
    plugin = next(
        p for g in robot.findall("gazebo") for p in g.findall("plugin") if p.get("filename") == "gz-sim-diff-drive-system"
    )
    assert float(plugin.find("max_linear_velocity").text) >= 1.0     # velocidade de cruzeiro pedida ao Nav2
    assert float(plugin.find("max_angular_velocity").text) >= 1.9    # giro máximo pedido ao Nav2


def test_lidar_sensor_publishes_scan(robot):
    sensor = next(s for g in robot.findall("gazebo") if g.get("reference") == "lidar_link" for s in g.findall("sensor"))
    assert sensor.get("type") == "gpu_lidar"
    assert sensor.find("topic").text == "scan"
    assert sensor.find("gz_frame_id").text == "lidar_link"


def test_collision_footprint_is_70_by_50(robot):
    base = link(robot, "base_link")
    sizes = [[float(v) for v in c.find("geometry/box").get("size").split()] for c in base.findall("collision")]
    assert [0.70, 0.50, 0.20] in sizes


def test_trunk_collision_box_matches_the_modelled_trunk_and_lid(robot):
    boxes = [c for c in link(robot, "base_link").findall("collision") if c.find("geometry/box").get("size").split()[2] == "0.21"]
    assert len(boxes) == 1
    assert [float(v) for v in boxes[0].find("geometry/box").get("size").split()] == pytest.approx([0.58, 0.48, 0.21])
    assert xyz(boxes[0]) == pytest.approx([-0.05, 0.0, 0.36])


# As malhas saem do Blender em coordenadas do base_link; o visual de cada link desfaz o deslocamento da sua junta.
MESHES = {
    "base_link": ("geraldo_body.obj", [0.0, 0.0, 0.0]),
    "wheel_left_link": ("roda_esq.obj", [-0.10, -0.225, -0.10]),
    "wheel_right_link": ("roda_dir.obj", [-0.10, 0.225, -0.10]),
    "caster_swivel_link": ("rodizio_garfo.obj", [0.25, 0.0, -0.09]),
    "caster_wheel_link": ("rodizio_roda.obj", [0.265, 0.0, -0.04]),
}


@pytest.mark.parametrize("name", MESHES)
def test_each_visual_mesh_exists_and_lands_in_the_base_frame(robot, name):
    mesh_file, offset = MESHES[name]
    visual = link(robot, name).find("visual")
    assert visual.find("geometry/mesh").get("filename") == f"package://geraldo_description/meshes/{mesh_file}"
    assert (PKG / "meshes" / mesh_file).is_file()
    origin = visual.find("origin")
    assert (origin is None and offset == [0.0, 0.0, 0.0]) or xyz(visual) == pytest.approx(offset)


RANGE_LAYOUT = {  # nome: (x, y, yaw em radianos); nenhum sensor a 180 graus (a traseira fica livre)
    "front_c": (0.36, 0.0, 0.0),
    "front_l45": (0.33, 0.26, 0.7854),
    "front_r45": (0.33, -0.26, -0.7854),
    "rear_l135": (-0.33, 0.26, 2.3562),
    "rear_r135": (-0.33, -0.26, -2.3562),
}


@pytest.mark.parametrize("name", RANGE_LAYOUT)
def test_range_sensor_sits_on_the_chassis_pointing_where_the_contract_says(robot, name):
    joint = joints(robot)[f"range_{name}_joint"]
    x, y, yaw = RANGE_LAYOUT[name]
    assert joint.get("type") == "fixed" and joint.find("parent").get("link") == "base_link"
    assert xyz(joint) == pytest.approx([x, y, 0.15])
    assert float(joint.find("origin").get("rpy").split()[2]) == pytest.approx(yaw)


@pytest.mark.parametrize("name", RANGE_LAYOUT)
def test_range_sensor_publishes_a_narrow_short_range_scan(robot, name):
    sensor = next(s for g in robot.findall("gazebo") if g.get("reference") == f"range_{name}_link" for s in g.findall("sensor"))
    assert sensor.get("type") == "gpu_lidar"
    assert sensor.find("topic").text == f"range/{name}"
    assert sensor.find("gz_frame_id").text == f"range_{name}_link"
    assert int(sensor.find("lidar/scan/horizontal/samples").text) == 5
    assert float(sensor.find("lidar/range/max").text) == pytest.approx(2.0)
