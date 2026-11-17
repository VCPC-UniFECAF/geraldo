import json
import struct
import zlib

import pytest
import yaml

from robot.scripts.export_map_png import JSON_NAME, MAP_YAML, OUT_DIR, PNG_NAME, convert, read_pgm, write_png


def decode_png(png: bytes) -> tuple[int, int, bytes]:
    """Decodificador mínimo para o que write_png produz (cinza de 8 bits, filtro 0)."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        kind, body = png[pos + 4 : pos + 8], png[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(kind + body)
        if kind == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", body[:10])
            assert (depth, color) == (8, 0)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    rows = [raw[y * (width + 1) : (y + 1) * (width + 1)] for y in range(height)]
    assert all(r[0] == 0 for r in rows)
    return width, height, b"".join(r[1:] for r in rows)


def test_read_pgm_returns_size_and_pixels():
    assert read_pgm(b"P5\n3 2\n255\n" + bytes([0, 254, 0, 254, 0, 254])) == (3, 2, bytes([0, 254, 0, 254, 0, 254]))


@pytest.mark.parametrize("bad", [b"P6\n1 1\n255\n\x00", b"P5\n2 2\n255\n\x00", b"lixo"])
def test_read_pgm_rejects_what_it_cannot_read_with_a_hint(bad):
    with pytest.raises(ValueError, match="gen_hospital.py|PGM"):
        read_pgm(bad)


def test_png_round_trips_the_pixels():
    pixels = bytes(range(12))
    assert decode_png(write_png(4, 3, pixels)) == (4, 3, pixels)


def test_convert_writes_png_and_metadata_from_the_nav2_map(tmp_path):
    convert(MAP_YAML, tmp_path)
    meta = yaml.safe_load(MAP_YAML.read_text())
    width, height, pixels = read_pgm((MAP_YAML.parent / meta["image"]).read_bytes())
    assert decode_png((tmp_path / PNG_NAME).read_bytes()) == (width, height, pixels)
    assert json.loads((tmp_path / JSON_NAME).read_text()) == {
        "image": PNG_NAME,
        "width": width,
        "height": height,
        "resolution": meta["resolution"],
        "origin": meta["origin"],
        "occupied_thresh": meta["occupied_thresh"],
        "free_thresh": meta["free_thresh"],
        "negate": meta["negate"],
    }


def test_the_committed_web_assets_match_the_nav2_map(tmp_path):
    convert(MAP_YAML, tmp_path)
    assert decode_png((OUT_DIR / PNG_NAME).read_bytes()) == decode_png((tmp_path / PNG_NAME).read_bytes())
    assert json.loads((OUT_DIR / JSON_NAME).read_text()) == json.loads((tmp_path / JSON_NAME).read_text())
