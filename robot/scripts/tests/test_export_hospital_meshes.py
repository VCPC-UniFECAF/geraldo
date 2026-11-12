import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COMMITTED = ROOT / "robot/ros2_ws/src/geraldo_description/meshes/hospital"
NAMES = ("hospital_estrutura", "hospital_mobiliario", "hospital_obstaculos", "maca")


def vertices(path):
    return [tuple(float(v) for v in l.split()[1:4]) for l in path.read_text().splitlines() if l.startswith("v ")]


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender ausente")
def test_building_and_exporting_the_hospital_reproduces_the_committed_meshes(tmp_path):
    blend = tmp_path / "hospital.blend"
    env = {**os.environ, "HOSPITAL_BLEND": str(blend), "NO_RENDER": "1"}
    subprocess.run(["blender", "-b", "--python", str(ROOT / "modelos-3d/build_hospital.py")], check=True, capture_output=True, text=True, timeout=600, env=env)
    subprocess.run(["blender", "-b", str(blend), "--python", str(ROOT / "robot/scripts/export_hospital_mesh.py"), "--", str(tmp_path)],
                   check=True, capture_output=True, text=True, timeout=600)
    for name in NAMES:
        new, old = vertices(tmp_path / f"{name}.obj"), vertices(COMMITTED / f"{name}.obj")
        assert len(new) == len(old), name
        for axis in range(3):
            assert min(v[axis] for v in new) == pytest.approx(min(v[axis] for v in old), abs=1e-4), name
            assert max(v[axis] for v in new) == pytest.approx(max(v[axis] for v in old), abs=1e-4), name
