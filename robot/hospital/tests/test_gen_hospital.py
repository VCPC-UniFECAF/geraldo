from pathlib import Path

import numpy as np
import pytest

from robot.hospital import gen_hospital as g

ROOT = Path(__file__).resolve().parents[3]
SPEC = g.load_spec(ROOT / "robot" / "hospital" / "hospital.yaml")
INFLATE_CELLS = round((SPEC["robot_inscribed_radius"] + SPEC["robot_margin"]) / SPEC["resolution"])
NORTH_CORRIDOR_BLOCK = (22.0, 28.0, 24.0, 30.0)  # maca no cruzamento do corredor norte


def all_waypoints():
    out = {}
    for room in SPEC["rooms"]:
        for wp in room["waypoints"]:
            out[wp["id"]] = (room, wp)
    return out


@pytest.fixture(scope="module")
def grid():
    return g.rasterize(SPEC)


@pytest.fixture(scope="module")
def inflated(grid):
    return g.inflate(grid, INFLATE_CELLS)


def test_room_ids_match_the_contract():
    assert {r["id"] for r in SPEC["rooms"]} == {
        "farmacia", "banco_sangue", "apoio", "centro_cirurgico", "uti", "pronto_socorro",
        "recepcao", "consultorio1", "consultorio2", "enfermaria214", "enfermaria215",
    }


def test_every_waypoint_is_inside_its_room_with_margin():
    for wid, (room, wp) in all_waypoints().items():
        x0, y0, x1, y1 = room["rect"]
        x, y = wp["xy"]
        assert x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5, wid


def test_every_stop_points_to_a_real_waypoint():
    wps = all_waypoints()
    for room in SPEC["rooms"]:
        if room.get("stop"):
            assert room["stop"] in wps, room["id"]


def test_waypoints_are_free_after_inflation(inflated):
    for wid, (_, wp) in all_waypoints().items():
        r, c = g.cell_of(*wp["xy"], SPEC)
        assert not inflated[r, c], wid


def test_all_waypoints_reachable_from_base(inflated):
    r, c = g.cell_of(*all_waypoints()["base_robo"][1]["xy"], SPEC)
    dist = g.distances(inflated, (r, c))
    unreachable = [w for w, (_, wp) in all_waypoints().items() if dist[g.cell_of(*wp["xy"], SPEC)] < 0]
    assert not unreachable, unreachable


def test_alternative_route_exists_when_north_corridor_is_blocked(grid):
    blocked = g.inflate(g.rasterize(SPEC, extra_obstacles=[NORTH_CORRIDOR_BLOCK]), INFLATE_CELLS)
    free = g.inflate(grid, INFLATE_CELLS)
    wps = all_waypoints()
    src = g.cell_of(*wps["banco_sangue_retirada"][1]["xy"], SPEC)
    dst = g.cell_of(*wps["cc_entrega"][1]["xy"], SPEC)
    normal = g.distances(free, src)[dst]
    detour = g.distances(blocked, src)[dst]
    assert normal > 0, "sem rota normal"
    assert detour > 0, "sem rota alternativa com a maca"
    assert detour > 2 * normal, f"a rota alternativa deveria ser bem mais longa ({detour} vs {normal})"


def test_doors_are_open_at_their_center(grid):
    for room in SPEC["rooms"]:
        x0, y0, x1, y1 = room["rect"]
        for d in room["doors"]:
            at = d["at"]
            probe = {"N": (at, y1), "S": (at, y0), "W": (x0, at), "E": (x1, at)}[d["wall"]]
            r, c = g.cell_of(*probe, SPEC)
            assert not grid[r, c], f"{room['id']} porta {d}"


def free_run(grid, cells):
    """Largura (em células) do trecho livre que contém o centro da lista de células."""
    mid = len(cells) // 2
    lo = hi = mid
    while lo > 0 and not grid[cells[lo - 1]]:
        lo -= 1
    while hi < len(cells) - 1 and not grid[cells[hi + 1]]:
        hi += 1
    return hi - lo + 1


def test_doors_open_a_passage_wider_than_the_robot(grid):
    res = SPEC["resolution"]
    ks = range(-30, 31)
    for room in SPEC["rooms"]:
        x0, y0, x1, y1 = room["rect"]
        for d in room["doors"]:
            at = d["at"]
            if d["wall"] in ("N", "S"):
                y = y1 if d["wall"] == "N" else y0
                cells = [g.cell_of(at + k * res, y, SPEC) for k in ks]
            else:
                x = x1 if d["wall"] == "E" else x0
                cells = [g.cell_of(x, at + k * res, SPEC) for k in ks]
            width = free_run(grid, cells) * res
            assert width >= SPEC["door_width"] - res, f"{room['id']} porta {d}: abertura de {width:.2f} m"


def test_outputs_are_written(tmp_path):
    out = {
        "world": tmp_path / "hospital.sdf",
        "map_dir": tmp_path / "maps",
        "locais": tmp_path / "locais.json",
        "waypoints": tmp_path / "waypoints.yaml",
    }
    g.generate(ROOT / "robot" / "hospital" / "hospital.yaml", **out)
    assert out["world"].read_text().startswith("<?xml")
    pgm = (out["map_dir"] / "hospital.pgm").read_bytes()
    assert pgm.startswith(b"P5\n920 600\n255\n")
    assert len(pgm) == len(b"P5\n920 600\n255\n") + 920 * 600
    assert "resolution: 0.05" in (out["map_dir"] / "hospital.yaml").read_text()
    import json
    locais = json.loads(out["locais"].read_text(encoding="utf-8"))
    assert {l["id"] for l in locais} == {r["id"] for r in SPEC["rooms"]}
    assert next(l for l in locais if l["id"] == "farmacia")["waypoint"] == "farmacia_balcao"
    assert next(l for l in locais if l["id"] == "recepcao")["waypoint"] is None
    import yaml
    wps = yaml.safe_load(out["waypoints"].read_text(encoding="utf-8"))["waypoints"]
    assert wps["cc_entrega"] == {"room": "centro_cirurgico", "x": 29, "y": 25, "yaw": 90}
