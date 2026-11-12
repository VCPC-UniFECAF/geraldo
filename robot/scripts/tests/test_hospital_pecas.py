import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load_paleta():
    spec = importlib.util.spec_from_file_location("hospital_paleta", ROOT / "modelos-3d/hospital_paleta.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PALETA


def test_palette_entries_are_color_roughness_metal():
    for name, (color, rough, metal) in load_paleta().items():
        assert len(color) == 3 and all(0 <= c <= 1 for c in color), name
        assert 0 <= rough <= 1 and 0 <= metal <= 1, name
