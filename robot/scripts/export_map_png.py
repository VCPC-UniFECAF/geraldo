"""Converte o mapa do Nav2 (hospital.pgm + hospital.yaml) em PNG e JSON para a visão 2D do app.

Uso: python3 robot/scripts/export_map_png.py   (escreve web/public/sim/hospital.png e hospital.json)
"""
import json
import struct
import zlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MAP_YAML = ROOT / "robot/ros2_ws/src/geraldo_nav/maps/hospital.yaml"
OUT_DIR = ROOT / "web/public/sim"
PNG_NAME = "hospital.png"
JSON_NAME = "hospital.json"


def read_pgm(data: bytes) -> tuple[int, int, bytes]:
    """PGM binário (P5, 255 níveis, sem comentários), como o gen_hospital.py escreve. Devolve (largura, altura, pixels)."""
    try:
        magic, dims, maxval, pixels = data.split(b"\n", 3)
        width, height = (int(n) for n in dims.split())
    except ValueError as err:
        raise ValueError("Mapa ilegível. Gere de novo com python3 robot/hospital/gen_hospital.py.") from err
    if magic != b"P5" or maxval != b"255":
        raise ValueError("Esperava um PGM binário (P5) com 255 níveis. Gere de novo com python3 robot/hospital/gen_hospital.py.")
    if len(pixels) != width * height:
        raise ValueError(f"O PGM declara {width}x{height}, mas tem {len(pixels)} pixels. Gere o mapa de novo.")
    return width, height, pixels


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def write_png(width: int, height: int, pixels: bytes) -> bytes:
    """PNG em tons de cinza de 8 bits, sem filtro (só a biblioteca padrão)."""
    rows = b"".join(b"\x00" + pixels[y * width : (y + 1) * width] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(rows, 9)) + _chunk(b"IEND", b"")


def convert(map_yaml: Path = MAP_YAML, out_dir: Path = OUT_DIR) -> None:
    meta = yaml.safe_load(map_yaml.read_text(encoding="utf-8"))
    width, height, pixels = read_pgm((map_yaml.parent / meta["image"]).read_bytes())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / PNG_NAME).write_bytes(write_png(width, height, pixels))
    info = {
        "image": PNG_NAME,
        "width": width,
        "height": height,
        "resolution": meta["resolution"],
        "origin": meta["origin"],
        "occupied_thresh": meta["occupied_thresh"],
        "free_thresh": meta["free_thresh"],
        "negate": meta["negate"],
    }
    (out_dir / JSON_NAME).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    convert()
    print(f"gerado: {OUT_DIR / PNG_NAME} e {OUT_DIR / JSON_NAME}")
