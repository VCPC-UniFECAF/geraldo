"""Confere as malhas do hospital que estão no repositório (sem precisar do Blender)."""
import json
import re
from pathlib import Path

import pytest

from robot.scripts.tests.test_hospital_pecas import load_paleta

ROOT = Path(__file__).resolve().parents[3]
MESHES = ROOT / "robot/ros2_ws/src/geraldo_description/meshes/hospital"
WORLD = ROOT / "robot/ros2_ws/src/geraldo_description/worlds/hospital.sdf"
NAMES = ("hospital_estrutura", "hospital_mobiliario", "hospital_obstaculos", "maca")
LAYOUT = json.loads((ROOT / "robot/hospital/hospital_layout.json").read_text(encoding="utf-8"))


def obj_text(name):
    return (MESHES / f"{name}.obj").read_text()


def vertices(name):
    return [tuple(float(v) for v in l.split()[1:4]) for l in obj_text(name).splitlines() if l.startswith("v ")]


@pytest.mark.parametrize("name", NAMES)
def test_each_obj_has_its_mtl_and_only_palette_materials(name):
    assert f"mtllib {name}.mtl" in obj_text(name)
    defined = set(re.findall(r"^newmtl (\S+)", (MESHES / f"{name}.mtl").read_text(), re.M))
    assert set(re.findall(r"^usemtl (\S+)", obj_text(name), re.M)) <= defined
    assert defined <= set(load_paleta()), defined - set(load_paleta())


@pytest.mark.parametrize("name", NAMES[:3])
def test_world_meshes_fit_the_46_by_30_building(name):
    xs, ys, zs = zip(*vertices(name))
    assert -0.2 <= min(xs) and max(xs) <= 46.2 and -0.2 <= min(ys) and max(ys) <= 30.2
    assert 0 <= min(zs) and max(zs) <= 2.6


def test_every_furniture_and_obstacle_piece_is_an_object_in_its_mesh():
    for name, group in (("hospital_mobiliario", "mobiliario"), ("hospital_obstaculos", "obstaculo")):
        objects = set(re.findall(r"^o (\S+)", obj_text(name), re.M))
        assert objects == {p["id"] for p in LAYOUT["pieces"] if p["group"] == group}, name


def test_stretcher_mesh_is_centered_at_its_own_origin_and_unrotated():
    xs, ys, zs = zip(*vertices("maca"))
    assert (min(xs) + max(xs)) / 2 == pytest.approx(0, abs=0.05) and (min(ys) + max(ys)) / 2 == pytest.approx(0, abs=0.05)
    assert max(xs) - min(xs) == pytest.approx(2.0, abs=0.05) and max(ys) - min(ys) == pytest.approx(0.8, abs=0.05)


def test_total_triangles_are_under_the_budget():
    total = 0
    for name in NAMES:
        for line in obj_text(name).splitlines():
            if line.startswith("f "):
                total += len(line.split()) - 3
    assert total <= 500_000, total


def test_world_sdf_references_only_existing_hospital_meshes():
    uris = re.findall(r"package://geraldo_description/(meshes/hospital/[\w.]+)", WORLD.read_text())
    assert {Path(u).stem for u in uris} == set(NAMES[:3])
    assert all((ROOT / "robot/ros2_ws/src/geraldo_description" / u).exists() for u in uris)


LIDAR_HEIGHT = 0.259   # robot/.../geraldo.urdf.xacro: lidar_joint em z = 0,259


def stretcher_solid_at_lidar_height(vertices_):
    """A maca precisa ter corpo (não só pernas) na altura do LiDAR, senão o Nav2 não a enxerga e o robô bate nela."""
    top = [v for v in vertices_ if abs(v[2] - 0.48) < 1e-3]   # topo da carenagem sob o colchão
    low = [v for v in vertices_ if abs(v[2] - 0.12) < 1e-3]   # base da carenagem (e pés das pernas)
    return bool(top) and bool(low) and max(abs(v[0]) for v in top) >= 0.9 and max(abs(v[1]) for v in top) >= 0.3 and 0.12 < LIDAR_HEIGHT < 0.48


def test_stretcher_has_a_solid_body_at_the_lidar_height():
    assert stretcher_solid_at_lidar_height(vertices("maca"))
