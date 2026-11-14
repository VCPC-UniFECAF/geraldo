#!/usr/bin/env python3
"""Gera mundo (SDF), mapa de ocupação, locais.json e waypoints.yaml a partir de robot/hospital/hospital.yaml.

Referencial: origem no canto sudoeste; x para leste, y para norte (metros).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # permite rodar como script (python3 robot/hospital/gen_hospital.py)
from robot.hospital.pieces import MOBILIARIO, OBSTACULO, PIECES  # noqa: E402
Segment = tuple[float, float, float, float]  # x0, y0, x1, y1 (eixo alinhado)


def load_spec(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


# ---------- geometria das paredes ----------
def _with_gaps(p0: float, p1: float, gaps: list[float], door_w: float) -> list[tuple[float, float]]:
    """Divide o intervalo [p0, p1] deixando vãos de largura door_w centrados em `gaps`."""
    cuts = sorted((a - door_w / 2, a + door_w / 2) for a in gaps)
    out, cur = [], p0
    for lo, hi in cuts:
        if lo > cur:
            out.append((cur, lo))
        cur = max(cur, hi)
    if cur < p1:
        out.append((cur, p1))
    return out


def _wall(wall: str, rect: tuple[float, float, float, float], gaps: list[float], door_w: float) -> list[Segment]:
    x0, y0, x1, y1 = rect
    if wall in ("N", "S"):
        y = y1 if wall == "N" else y0
        return [(a, y, b, y) for a, b in _with_gaps(x0, x1, gaps, door_w)]
    x = x1 if wall == "E" else x0
    return [(x, a, x, b) for a, b in _with_gaps(y0, y1, gaps, door_w)]


def wall_segments(spec: dict) -> list[Segment]:
    # cada ponta de parede é engrossada em meia espessura; alargamos o vão para a abertura livre ficar com door_width
    door_w = spec["door_width"] + spec["wall_thickness"]
    segs: list[Segment] = []
    for room in spec["rooms"]:
        rect = tuple(room["rect"])
        for wall in "NSWE":
            gaps = [d["at"] for d in room["doors"] if d["wall"] == wall]
            segs += _wall(wall, rect, gaps, door_w)
    w, h = spec["size"]
    outer = (0.0, 0.0, float(w), float(h))
    for wall in "NSWE":
        gaps = [e["at"] for e in spec["entrances"] if e["wall"] == wall]
        segs += _wall(wall, outer, gaps, door_w)
    return segs


# ---------- peças (mobiliário, obstáculos, maca) ----------
Rect = tuple[float, float, float, float]
LANE_WIDTH = 1.2


def _placed(item: dict, key: str, group: str | None, default_room: str) -> dict:
    kind = item["type"]
    if kind not in PIECES:
        raise ValueError(f"peça desconhecida '{kind}'. Tipos válidos: {', '.join(sorted(PIECES))}")
    piece = PIECES[kind]
    if group and piece.group != group:
        raise ValueError(f"peça '{kind}' é do grupo '{piece.group}' e não pode ficar em '{group}'")
    yaw = item.get("yaw", 0)
    if yaw % 90:
        raise ValueError(f"peça '{kind}': yaw {yaw} precisa ser múltiplo de 90")
    w, d, h = piece.size
    if yaw % 180:
        w, d = d, w
    x, y = item["xy"]
    return {
        "id": key, "type": kind, "room": item.get("room", default_room), "xy": [x, y], "yaw": yaw,
        "size": list(piece.size), "z": piece.z, "group": piece.group, "walkable": piece.walkable,
        "rect": [x - w / 2, y - d / 2, x + w / 2, y + d / 2],
    }


def placed_pieces(spec: dict) -> list[dict]:
    """Todas as peças do YAML (mobiliário, obstáculos e a maca) com tamanho, grupo e retângulo no chão."""
    count: dict[str, int] = {}
    out = []
    for section, group in (("furniture", MOBILIARIO), ("obstacles", OBSTACULO)):
        for item in spec.get(section, []):
            n = count[item["type"]] = count.get(item["type"], 0) + 1
            out.append(_placed(item, f"{item['type']}_{n}", group, "corredor"))
    if "stretcher" in spec:
        stretcher = _placed(spec["stretcher"], "maca", None, "corredor")
        stretcher["group"] = "maca"
        out.append(stretcher)
    return out


def obstacle_rects(spec: dict) -> list[Rect]:
    return [tuple(p["rect"]) for p in placed_pieces(spec) if p["group"] == OBSTACULO]


def furniture_rects(spec: dict) -> list[Rect]:
    """Mobiliário que o LiDAR enxerga: fica fora do mapa do Nav2, mas não é obstáculo novo para a telemetria."""
    return [tuple(p["rect"]) for p in placed_pieces(spec) if p["group"] == MOBILIARIO and not p["walkable"]]


def stretcher_rect(spec: dict) -> Rect:
    return tuple(next(p for p in placed_pieces(spec) if p["group"] == "maca")["rect"])


def _door_points(room: dict) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = room["rect"]
    return [{"N": (d["at"], y1), "S": (d["at"], y0), "W": (x0, d["at"]), "E": (x1, d["at"])}[d["wall"]] for d in room["doors"]]


def lanes(spec: dict) -> dict[str, list[Rect]]:
    """Faixas que ficam livres de móveis: de cada porta até o ponto de parada (ou o centro da sala) e dos outros pontos até ele."""
    r = LANE_WIDTH / 2
    out = {}
    for room in spec["rooms"]:
        x0, y0, x1, y1 = room["rect"]
        stops = {wp["id"]: wp["xy"] for wp in room["waypoints"]}
        target = stops[room["stop"]] if room.get("stop") else [(x0 + x1) / 2, (y0 + y1) / 2]
        starts = _door_points(room) + [xy for xy in stops.values() if xy != target]
        out[room["id"]] = [
            (min(a[0], target[0]) - r, min(a[1], target[1]) - r, max(a[0], target[0]) + r, max(a[1], target[1]) + r)
            for a in starts
        ]
    return out


def door_centers(spec: dict) -> list[dict]:
    """Centro de cada vão (portas das salas e entradas); `axis` é a direção em que a parede corre."""
    doors = []
    for room in spec["rooms"]:
        for (x, y), d in zip(_door_points(room), room["doors"]):
            doors.append({"x": float(x), "y": float(y), "axis": "x" if d["wall"] in ("N", "S") else "y"})
    w, h = spec["size"]
    for e in spec["entrances"]:
        x, y = {"N": (e["at"], h), "S": (e["at"], 0), "W": (0, e["at"]), "E": (w, e["at"])}[e["wall"]]
        doors.append({"x": float(x), "y": float(y), "axis": "x" if e["wall"] in ("N", "S") else "y"})
    return doors


def build_layout(spec: dict) -> dict:
    """Tudo que o Blender precisa (ele não tem PyYAML): paredes, vãos, salas e peças."""
    return {
        "size": spec["size"],
        "wall_thickness": spec["wall_thickness"],
        "wall_height": spec["wall_height"],
        "door_width": spec["door_width"],
        "walls": [list(s) for s in wall_segments(spec)],
        "doors": door_centers(spec),
        "rooms": [{"id": r["id"], "kind": r["kind"], "rect": r["rect"]} for r in spec["rooms"]],
        "pieces": placed_pieces(spec),
    }


# ---------- mapa de ocupação ----------
def grid_shape(spec: dict) -> tuple[int, int]:
    res = spec["resolution"]
    w, h = spec["size"]
    return round(h / res), round(w / res)  # linhas, colunas


def cell_of(x: float, y: float, spec: dict) -> tuple[int, int]:
    rows, cols = grid_shape(spec)
    res = spec["resolution"]
    return min(rows - 1, max(0, rows - 1 - int(y / res))), min(cols - 1, max(0, int(x / res)))


def _fill(occ: np.ndarray, rect: tuple[float, float, float, float], spec: dict) -> None:
    rows, cols = occ.shape
    res = spec["resolution"]
    x0, y0, x1, y1 = rect
    c0, c1 = max(0, int(np.floor(x0 / res))), min(cols, int(np.ceil(x1 / res)))
    r0, r1 = max(0, rows - int(np.ceil(y1 / res))), min(rows, rows - int(np.floor(y0 / res)))
    occ[r0:r1, c0:c1] = True


def rasterize(spec: dict, extra_obstacles=()) -> np.ndarray:
    occ = np.zeros(grid_shape(spec), dtype=bool)
    half = spec["wall_thickness"] / 2
    for x0, y0, x1, y1 in wall_segments(spec):
        _fill(occ, (min(x0, x1) - half, min(y0, y1) - half, max(x0, x1) + half, max(y0, y1) + half), spec)
    for rect in extra_obstacles:
        _fill(occ, rect, spec)
    return occ


def _shift_or(dst: np.ndarray, src: np.ndarray, dr: int, dc: int) -> None:
    rows, cols = src.shape
    r0, r1 = max(0, dr), min(rows, rows + dr)
    c0, c1 = max(0, dc), min(cols, cols + dc)
    dst[r0:r1, c0:c1] |= src[r0 - dr : r1 - dr, c0 - dc : c1 - dc]


def inflate(occ: np.ndarray, radius_cells: int) -> np.ndarray:
    out = occ.copy()
    for dr in range(-radius_cells, radius_cells + 1):
        for dc in range(-radius_cells, radius_cells + 1):
            if dr * dr + dc * dc <= radius_cells * radius_cells and (dr or dc):
                _shift_or(out, occ, dr, dc)
    return out


def distances(blocked: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Distância em células (vizinhança de 4) a partir de `start`; -1 se inalcançável."""
    rows, cols = blocked.shape
    dist = np.full(blocked.shape, -1, dtype=np.int32)
    if blocked[start]:
        return dist
    dist[start] = 0
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        d = dist[r, c] + 1
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and not blocked[nr, nc] and dist[nr, nc] < 0:
                dist[nr, nc] = d
                queue.append((nr, nc))
    return dist


# ---------- escritores ----------
def write_pgm(occ: np.ndarray, path: Path) -> None:
    rows, cols = occ.shape
    pixels = np.where(occ, 0, 254).astype(np.uint8)  # 0 = ocupado (preto), 254 = livre
    path.write_bytes(f"P5\n{cols} {rows}\n255\n".encode("ascii") + pixels.tobytes())


def write_map_yaml(spec: dict, path: Path) -> None:
    path.write_text(
        "image: hospital.pgm\n"
        "mode: trinary\n"
        f"resolution: {spec['resolution']}\n"
        "origin: [0.0, 0.0, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.25\n",
        encoding="utf-8",
    )


MESH_URI = "package://geraldo_description/meshes/hospital"


def _box_model(name: str, cx: float, cy: float, sx: float, sy: float, h: float) -> str:
    return (
        f'    <model name="{name}"><static>true</static><pose>{cx:.3f} {cy:.3f} {h / 2:.3f} 0 0 0</pose>'
        f'<link name="link"><collision name="c"><geometry><box><size>{sx:.3f} {sy:.3f} {h:.3f}</size></box></geometry></collision></link></model>'
    )


def write_sdf(spec: dict, path: Path) -> None:
    """Mundo do Gazebo: o visual vem das malhas do Blender; as paredes e os obstáculos fixos só têm colisão em caixa."""
    t, h = spec["wall_thickness"], spec["wall_height"]
    models = []
    for i, (x0, y0, x1, y1) in enumerate(wall_segments(spec)):
        horizontal = abs(y1 - y0) < 1e-9
        length = abs(x1 - x0) if horizontal else abs(y1 - y0)
        if length < 1e-6:
            continue
        sx, sy = (length + t, t) if horizontal else (t, length + t)
        models.append(_box_model(f"wall_{i}", (x0 + x1) / 2, (y0 + y1) / 2, sx, sy, h))
    for p in placed_pieces(spec):
        if p["group"] == OBSTACULO:
            a, b, c, d = p["rect"]
            models.append(_box_model(f"obs_{p['id']}", (a + c) / 2, (b + d) / 2, c - a, d - b, p["size"][2]))
    visuals = "".join(
        f'<visual name="{n}"><geometry><mesh><uri>{MESH_URI}/{n}.obj</uri></mesh></geometry></visual>'
        for n in ("hospital_estrutura", "hospital_mobiliario", "hospital_obstaculos")
    )
    w, d = spec["size"]
    xml = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="hospital">
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>{w / 2} {d / 2} 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse><specular>0.2 0.2 0.2 1</specular><direction>-0.3 0.2 -1</direction></light>
    <model name="ground"><static>true</static><pose>{w / 2} {d / 2} 0 0 0 0</pose>
      <link name="link"><collision name="c"><geometry><plane><normal>0 0 1</normal><size>{w + 4} {d + 4}</size></plane></geometry></collision>
      <visual name="v"><pose>0 0 -0.02 0 0 0</pose><geometry><plane><normal>0 0 1</normal><size>{w + 4} {d + 4}</size></plane></geometry>
      <material><ambient>0.35 0.4 0.35 1</ambient><diffuse>0.35 0.4 0.35 1</diffuse></material></visual></link></model>
    <model name="hospital_visual"><static>true</static><link name="link">{visuals}</link></model>
{chr(10).join(models)}
  </world>
</sdf>
"""
    path.write_text(xml, encoding="utf-8")


def write_maca_sdf(spec: dict, path: Path) -> None:
    """Modelo da maca que bloqueia o corredor norte; entra no mundo em tempo de execução (robot/scripts/spawn_stretcher.sh)."""
    s = next(p for p in placed_pieces(spec) if p["group"] == "maca")
    (x, y), yaw = s["xy"], math.radians(s["yaw"])
    w, d, h = s["size"]
    path.write_text(
        f"""<?xml version="1.0"?>
<sdf version="1.9">
  <model name="maca"><static>true</static><pose>{x:.3f} {y:.3f} 0 0 0 {yaw:.4f}</pose>
    <link name="link">
      <collision name="c"><pose>0 0 {h / 2:.3f} 0 0 0</pose><geometry><box><size>{w:.3f} {d:.3f} {h:.3f}</size></box></geometry></collision>
      <visual name="v"><geometry><mesh><uri>{MESH_URI}/maca.obj</uri></mesh></geometry></visual>
    </link>
  </model>
</sdf>
""",
        encoding="utf-8",
    )


def write_locais(spec: dict, path: Path) -> None:
    locais = [
        {
            "id": r["id"],
            "name": r["name"],
            "kind": r["kind"],
            "has_stock": bool(r["stock"]),
            "waypoint": r.get("stop"),
        }
        for r in spec["rooms"]
    ]
    path.write_text(json.dumps(locais, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_waypoints(spec: dict, path: Path) -> None:
    wps = {}
    for r in spec["rooms"]:
        for wp in r["waypoints"]:
            x, y = wp["xy"]
            wps[wp["id"]] = {"room": r["id"], "x": x, "y": y, "yaw": wp["yaw"]}
    path.write_text(yaml.safe_dump({"waypoints": wps}, sort_keys=False, allow_unicode=True), encoding="utf-8")


def write_layout(spec: dict, path: Path) -> None:
    path.write_text(json.dumps(build_layout(spec), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def generate(spec_path, world, map_dir, locais, waypoints, layout=None, maca=None) -> None:
    spec = load_spec(spec_path)
    for p in (Path(world), Path(map_dir) / "x", Path(locais), Path(waypoints)):
        p.parent.mkdir(parents=True, exist_ok=True)
    write_sdf(spec, Path(world))
    occ = rasterize(spec, extra_obstacles=obstacle_rects(spec))
    write_pgm(occ, Path(map_dir) / "hospital.pgm")
    write_map_yaml(spec, Path(map_dir) / "hospital.yaml")
    (Path(map_dir) / "furniture.json").write_text(json.dumps([list(r) for r in furniture_rects(spec)]) + "\n", encoding="utf-8")
    write_locais(spec, Path(locais))
    write_waypoints(spec, Path(waypoints))
    if layout:
        Path(layout).parent.mkdir(parents=True, exist_ok=True)
        write_layout(spec, Path(layout))
    if maca:
        write_maca_sdf(spec, Path(maca))


def main() -> None:
    desc = ROOT / "robot/ros2_ws/src/geraldo_description"
    nav = ROOT / "robot/ros2_ws/src/geraldo_nav"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", default=str(ROOT / "robot/hospital/hospital.yaml"))
    ap.add_argument("--world", default=str(desc / "worlds/hospital.sdf"))
    ap.add_argument("--map-dir", default=str(nav / "maps"))
    ap.add_argument("--locais", default=str(ROOT / "backend/seeds/locais.json"))
    ap.add_argument("--waypoints", default=str(nav / "config/waypoints.yaml"))
    ap.add_argument("--layout", default=str(ROOT / "robot/hospital/hospital_layout.json"))
    ap.add_argument("--maca", default=str(desc / "worlds/maca.sdf"))
    a = ap.parse_args()
    generate(a.spec, a.world, a.map_dir, a.locais, a.waypoints, a.layout, a.maca)
    print("hospital gerado")


if __name__ == "__main__":
    main()
