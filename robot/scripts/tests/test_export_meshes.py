import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BLEND = ROOT / "modelos-3d/geraldoV3.blend"
COMMITTED = ROOT / "robot/ros2_ws/src/geraldo_description/meshes"
NAMES = ("geraldo_body", "roda_esq", "roda_dir", "rodizio_garfo", "rodizio_roda")


def vertices(path):
    return [tuple(float(v) for v in l.split()[1:4]) for l in path.read_text().splitlines() if l.startswith("v ")]


@pytest.mark.skipif(shutil.which("blender") is None or not BLEND.exists(), reason="Blender ou modelos-3d/geraldoV3.blend ausente")
def test_exporting_the_v3_blend_reproduces_the_committed_meshes(tmp_path):
    subprocess.run(
        ["blender", "-b", str(BLEND), "--python", str(ROOT / "robot/scripts/export_blender_mesh.py"), "--", str(tmp_path)],
        check=True, capture_output=True, text=True, timeout=300,
    )
    for name in NAMES:
        new, old = vertices(tmp_path / f"{name}.obj"), vertices(COMMITTED / f"{name}.obj")
        assert len(new) == len(old), name
        for axis in range(3):
            assert min(v[axis] for v in new) == pytest.approx(min(v[axis] for v in old), abs=1e-4), name
            assert max(v[axis] for v in new) == pytest.approx(max(v[axis] for v in old), abs=1e-4), name
