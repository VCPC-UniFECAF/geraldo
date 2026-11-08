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
