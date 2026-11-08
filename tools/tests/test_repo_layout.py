from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    "modelos-3d",
    "backend",
    "web",
    "security",
    "unity",
    "ros2_ws/src",
    "design-system",
    "hospital",
    "tools",
    "docs/contracts",
    "docs/prompts",
]

REQUIRED_FILES = [
    "README.md",
    ".gitignore",
    "modelos-3d/geraldoV1.blend",
    "modelos-3d/geraldoV1.glb",
    "modelos-3d/build_geraldoV1.py",
]


def test_required_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"pastas faltando: {missing}"


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"arquivos faltando: {missing}"


def test_model_files_are_not_empty():
    for name in ("geraldoV1.blend", "geraldoV1.glb"):
        assert (ROOT / "modelos-3d" / name).stat().st_size > 100_000, name


def test_renders_were_copied():
    renders = list((ROOT / "modelos-3d/renders").glob("*.png"))
    assert len(renders) >= 6
