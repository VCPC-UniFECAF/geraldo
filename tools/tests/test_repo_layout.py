from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    "modelos-3d",
    "backend",
    "web",
    "security",
    "unity",
    "robot/ros2_ws/src",
    "robot/scripts",
    "design-system",
    "robot/hospital",
    "tools",
    "docs/contracts",
]

REQUIRED_FILES = [
    "README.md",
    ".gitignore",
    "modelos-3d/geraldoV3.blend",
    "modelos-3d/render_geraldoV3.py",
    "modelos-3d/v1/geraldoV1.blend",
    "modelos-3d/v1/geraldoV1.glb",
    "modelos-3d/v1/build_geraldoV1.py",
]


def test_required_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"pastas faltando: {missing}"


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"arquivos faltando: {missing}"


def test_robot_front_is_not_scattered_in_the_root():
    scattered = [d for d in ("hospital", "ros2_ws") if (ROOT / d).exists()]
    assert not scattered, f"mover para robot/: {scattered}"


def test_model_files_are_not_empty():
    for name in ("geraldoV3.blend", "v1/geraldoV1.blend", "v1/geraldoV1.glb"):
        assert (ROOT / "modelos-3d" / name).stat().st_size > 100_000, name


def test_v3_renders_exist():
    views = ("hero", "frente", "traseira", "lateral", "topo", "aerea")
    missing = [v for v in views if not (ROOT / f"modelos-3d/renders/geraldoV3_{v}.png").is_file()]
    assert not missing, f"renders do V3 faltando: {missing}"
