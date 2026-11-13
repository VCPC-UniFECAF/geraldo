"""Confere as malhas do V3 que estão no repositório (sem precisar do Blender)."""
import re
from collections import defaultdict
from pathlib import Path

import pytest

MESHES = Path(__file__).resolve().parents[3] / "robot/ros2_ws/src/geraldo_description/meshes"
FILES = ("geraldo_body", "roda_esq", "roda_dir", "rodizio_garfo", "rodizio_roda")


def load(name):
    """Devolve {objeto: [(x, y, z), ...]} do .obj."""
    groups, current = defaultdict(list), None
    for line in (MESHES / f"{name}.obj").read_text().splitlines():
        if line.startswith("o "):
            current = line[2:].strip()
        elif line.startswith("v ") and current:
            groups[current].append(tuple(float(v) for v in line.split()[1:4]))
    return groups


def box(points):
    return [(min(p[i] for p in points), max(p[i] for p in points)) for i in range(3)]


def center(points):
    return [sum(p[i] for p in points) / len(points) for i in range(3)]


def every_point(name):
    return [p for pts in load(name).values() for p in pts]


@pytest.mark.parametrize("name", FILES)
def test_each_obj_has_its_material_file_with_every_material_defined(name):
    text = (MESHES / f"{name}.obj").read_text()
    assert f"mtllib {name}.mtl" in text
    defined = set(re.findall(r"^newmtl (\S+)", (MESHES / f"{name}.mtl").read_text(), re.M))
    assert set(re.findall(r"^usemtl (\S+)", text, re.M)) <= defined


def test_body_has_its_front_at_plus_x_like_the_urdf_lidar():
    # URDF: frente = +X, LiDAR em x = 0,275. Se o OBJ sair girado, o corpo fica de costas para as rodas e o rodízio.
    body = load("geraldo_body")
    assert center(body["camera_rgbd"])[0] > 0.3
    assert center(body["lidar"])[0] > 0.2
    assert center(body["painel"])[0] < -0.3


def test_body_leaves_out_the_cutters_the_wheels_and_the_caster():
    names = load("geraldo_body")
    assert len(names) > 40
    assert not [n for n in names if n.startswith(("corte_", "roda_", "rodizio_", "Camera", "Light"))]


def test_body_fits_the_70_by_50_footprint_and_is_under_half_a_metre():
    x, y, z = box(every_point("geraldo_body"))
    assert -0.36 < x[0] and x[1] < 0.37        # câmera e parafusos do painel saem poucos milímetros do chassi
    assert max(abs(y[0]), abs(y[1])) <= 0.251
    assert 0.04 <= z[0] and z[1] <= 0.47


@pytest.mark.parametrize("name, side", [("roda_esq", 1), ("roda_dir", -1)])
def test_big_wheels_sit_at_x_0_1_z_0_1_on_their_own_side(name, side):
    x, y, z = box(every_point(name))
    assert (x[0], x[1], z[0], z[1]) == pytest.approx((0.0, 0.2, 0.0, 0.2), abs=1e-3)   # raio de 0,10 m
    near, far = sorted((abs(y[0]), abs(y[1])))
    assert near == pytest.approx(0.205, abs=1e-3)                # face de dentro do pneu
    assert far > 0.245                                           # o cubo sai da face de fora
    assert side * (y[0] + y[1]) > 0                              # e está do lado certo do robô


def test_caster_parts_match_the_urdf_joints():
    wheel = every_point("rodizio_roda")
    assert center(wheel) == pytest.approx([-0.265, 0.0, 0.04], abs=1e-3)      # eixo da roda pequena
    x, y, z = box(wheel)
    assert (z[0], z[1]) == pytest.approx((0.0, 0.08), abs=1e-3)               # apoiada no chão
    fork = box(every_point("rodizio_garfo"))
    assert fork[2][0] > 0.03 and fork[2][1] <= 0.098                          # garfo acima do chão, sob o chassi
