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


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def z_overlaps(p, q):
    return p["z"] < q["z"] + q["size"][2] and q["z"] < p["z"] + p["size"][2]


@pytest.fixture(scope="module")
def pieces():
    return g.placed_pieces(SPEC)


def test_every_room_has_furniture_and_the_hospital_has_four_fixed_obstacles(pieces):
    rooms_with_pieces = {p["room"] for p in pieces}
    assert {r["id"] for r in SPEC["rooms"]} <= rooms_with_pieces
    assert len([p for p in pieces if p["group"] == "obstaculo"]) >= 4
    assert g.stretcher_rect(SPEC)


def test_furniture_is_inside_its_room_with_a_margin(pieces):
    rooms = {r["id"]: r["rect"] for r in SPEC["rooms"]}
    half = SPEC["wall_thickness"] / 2 - 1e-9
    for p in pieces:
        if p["room"] == "corredor":
            continue
        x0, y0, x1, y1 = rooms[p["room"]]
        a, b, c, d = p["rect"]
        assert x0 + half <= a and y0 + half <= b and c <= x1 - half and d <= y1 - half, p["id"]


def test_corridor_pieces_stay_outside_the_rooms_and_inside_the_building(pieces):
    w, h = SPEC["size"]
    for p in pieces:
        if p["room"] != "corredor":
            continue
        a, b, c, d = p["rect"]
        assert 0 <= a and 0 <= b and c <= w and d <= h, p["id"]
        assert not any(overlaps(p["rect"], r["rect"]) for r in SPEC["rooms"]), p["id"]


def test_door_to_waypoint_lanes_are_free_of_furniture(pieces):
    lanes = g.lanes(SPEC)
    for p in pieces:
        if p["room"] == "corredor" or p["walkable"]:
            continue
        for lane in lanes[p["room"]]:
            assert not overlaps(p["rect"], lane), f"{p['id']} bloqueia a faixa de {p['room']}"


def test_pieces_do_not_overlap_each_other(pieces):
    solid = [p for p in pieces if not p["walkable"]]
    for i, p in enumerate(solid):
        for q in solid[i + 1:]:
            assert not (overlaps(p["rect"], q["rect"]) and z_overlaps(p, q)), f"{p['id']} x {q['id']}"


def test_fixed_obstacles_keep_every_waypoint_reachable():
    blocked = g.inflate(g.rasterize(SPEC, extra_obstacles=g.obstacle_rects(SPEC)), INFLATE_CELLS)
    wps = all_waypoints()
    dist = g.distances(blocked, g.cell_of(*wps["base_robo"][1]["xy"], SPEC))
    unreachable = [w for w, (_, wp) in wps.items() if dist[g.cell_of(*wp["xy"], SPEC)] < 0]
    assert not unreachable, unreachable


def test_stretcher_still_leaves_a_longer_alternative_route():
    fixed = g.obstacle_rects(SPEC)
    free = g.inflate(g.rasterize(SPEC, extra_obstacles=fixed), INFLATE_CELLS)
    blocked = g.inflate(g.rasterize(SPEC, extra_obstacles=fixed + [g.stretcher_rect(SPEC)]), INFLATE_CELLS)
    wps = all_waypoints()
    src = g.cell_of(*wps["banco_sangue_retirada"][1]["xy"], SPEC)
    dst = g.cell_of(*wps["cc_entrega"][1]["xy"], SPEC)
    normal, detour = g.distances(free, src)[dst], g.distances(blocked, src)[dst]
    assert normal > 0 and detour > 2 * normal, (normal, detour)


def test_unknown_piece_type_fails_with_a_clear_message():
    spec = {**SPEC, "furniture": [{"room": "recepcao", "type": "sofa", "xy": [5, 5]}]}
    with pytest.raises(ValueError, match="sofa.*Tipos válidos"):
        g.placed_pieces(spec)


def test_obstacle_types_cannot_be_used_as_furniture():
    spec = {**SPEC, "furniture": [{"room": "recepcao", "type": "cadeira_rodas", "xy": [5, 5]}]}
    with pytest.raises(ValueError, match="cadeira_rodas"):
        g.placed_pieces(spec)


def test_fixed_obstacles_are_black_in_the_generated_map(tmp_path):
    out = {"world": tmp_path / "w.sdf", "map_dir": tmp_path / "maps", "locais": tmp_path / "l.json", "waypoints": tmp_path / "w.yaml"}
    g.generate(ROOT / "robot" / "hospital" / "hospital.yaml", **out)
    pgm = (out["map_dir"] / "hospital.pgm").read_bytes()
    pixels = pgm[len(b"P5\n920 600\n255\n"):]
    first = next(p for p in g.placed_pieces(SPEC) if p["group"] == "obstaculo")
    r, c = g.cell_of(*first["xy"], SPEC)
    assert pixels[r * 920 + c] == 0


def test_layout_json_describes_walls_doors_rooms_and_pieces(tmp_path):
    layout = g.build_layout(SPEC)
    assert layout["size"] == [46, 30]
    assert len(layout["walls"]) == len(g.wall_segments(SPEC))
    assert {r["id"] for r in layout["rooms"]} == {r["id"] for r in SPEC["rooms"]}
    assert len(layout["doors"]) == sum(len(r["doors"]) for r in SPEC["rooms"]) + len(SPEC["entrances"])
    assert {"x": 7.0, "y": 16.0, "axis": "x"} in layout["doors"]       # porta sul da farmácia
    assert {p["id"] for p in layout["pieces"]} == {p["id"] for p in g.placed_pieces(SPEC)}
    out = tmp_path / "layout.json"
    g.generate(ROOT / "robot" / "hospital" / "hospital.yaml", world=tmp_path / "w.sdf", map_dir=tmp_path / "m",
               locais=tmp_path / "l.json", waypoints=tmp_path / "w.yaml", layout=out)
    import json
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(json.dumps(layout))
