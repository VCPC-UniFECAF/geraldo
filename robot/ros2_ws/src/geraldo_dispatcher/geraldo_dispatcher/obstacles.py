import math
from collections.abc import Callable
from pathlib import Path

import yaml

from .waypoints import Pose

LIDAR_X = 0.275          # m: o lidar_link fica 27,5 cm à frente do base_link (geraldo.urdf.xacro)
STATIC_TOLERANCE = 0.25  # m: um ponto a menos disso de uma parede do mapa é a própria parede (erro do AMCL e do mapa)
CLUSTER_GAP = 0.35       # m: pontos a menos disso um do outro formam o mesmo obstáculo
MAX_OBSTACLES = 20       # contrato: Telemetry.obstacles
MIN_RADIUS = 0.10        # m


class StaticMap:
    """Mapa de ocupação do hospital (o hospital.yaml + hospital.pgm do Nav2), só para saber o que já é parede."""

    def __init__(self, width: int, height: int, resolution: float, origin: tuple[float, float], occupied: bytes) -> None:
        self.width, self.height, self.resolution, self.origin = width, height, resolution, origin
        self._occupied = occupied  # uma linha por vez, de baixo (y menor) para cima; 1 = ocupada

    @classmethod
    def from_yaml(cls, yaml_path) -> "StaticMap":
        yaml_path = Path(yaml_path)
        meta = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        raw = (yaml_path.parent / meta["image"]).read_bytes()
        magic, width, height, maxval, pixels = _parse_pgm(raw)
        threshold = float(meta["occupied_thresh"])
        negate = int(meta.get("negate", 0))
        rows = []
        for row in range(height - 1, -1, -1):  # o PGM começa pelo topo; o mapa, por baixo
            chunk = pixels[row * width:(row + 1) * width]
            rows.append(bytes(1 if _occupancy(p / maxval, negate) > threshold else 0 for p in chunk))
        return cls(width, height, float(meta["resolution"]), (float(meta["origin"][0]), float(meta["origin"][1])), b"".join(rows))

    def occupied_near(self, x: float, y: float, radius: float) -> bool:
        """True se há célula ocupada a até `radius` m de (x, y). Fora do mapa conta como ocupado (não é um obstáculo novo)."""
        col = math.floor((x - self.origin[0]) / self.resolution)
        row = math.floor((y - self.origin[1]) / self.resolution)
        if not (0 <= col < self.width and 0 <= row < self.height):
            return True
        reach = math.ceil(radius / self.resolution)
        for r in range(max(0, row - reach), min(self.height, row + reach + 1)):
            for c in range(max(0, col - reach), min(self.width, col + reach + 1)):
                if self._occupied[r * self.width + c] and math.hypot(c - col, r - row) * self.resolution <= radius:
                    return True
        return False


def _parse_pgm(raw: bytes) -> tuple[str, int, int, int, bytes]:
    """PGM binário (P5): devolve (magic, largura, altura, valor máximo, pixels)."""
    fields, pos = [], 0
    while len(fields) < 4:
        while raw[pos:pos + 1].isspace():
            pos += 1
        if raw[pos:pos + 1] == b"#":
            pos = raw.index(b"\n", pos)
            continue
        end = pos
        while not raw[end:end + 1].isspace():
            end += 1
        fields.append(raw[pos:end])
        pos = end
    pos += 1  # um único espaço separa o cabeçalho dos pixels
    if fields[0] != b"P5":
        raise ValueError("Mapa em formato PGM não suportado: use P5 (binário).")
    return "P5", int(fields[1]), int(fields[2]), int(fields[3]), raw[pos:]


def _occupancy(brightness: float, negate: int) -> float:
    """Probabilidade de ocupação de um pixel (convenção do map_server: pixel escuro = ocupado, a menos de `negate`)."""
    return brightness if negate else 1.0 - brightness


def detect_obstacles(ranges: list[float], angle_min: float, angle_increment: float, pose: Pose,
                     is_static: Callable[[float, float], bool], range_min: float = 0.12, range_max: float = 12.0,
                     lidar_x: float = LIDAR_X, cluster_gap: float = CLUSTER_GAP,
                     max_obstacles: int = MAX_OBSTACLES) -> list[tuple[float, float, float]]:
    """Obstáculos que o LiDAR vê e o mapa não tem, como círculos (x, y, raio) em metros no referencial `map`.

    Cada feixe com retorno vira um ponto no `map` (pela pose do AMCL); o que `is_static` reconhece como parede é
    descartado; o resto é agrupado por proximidade. Os `max_obstacles` grupos mais próximos do robô saem primeiro.
    """
    cos_yaw, sin_yaw = math.cos(pose.yaw), math.sin(pose.yaw)
    points = []
    for i, r in enumerate(ranges):
        if not (math.isfinite(r) and range_min <= r < range_max - 0.01):
            continue
        angle = angle_min + i * angle_increment
        bx, by = lidar_x + r * math.cos(angle), r * math.sin(angle)  # no base_link
        x, y = pose.x + bx * cos_yaw - by * sin_yaw, pose.y + bx * sin_yaw + by * cos_yaw
        if not is_static(x, y):
            points.append((x, y))
    clusters = _cluster(points, cluster_gap)
    circles = []
    for members in clusters:
        cx = sum(p[0] for p in members) / len(members)
        cy = sum(p[1] for p in members) / len(members)
        radius = max(MIN_RADIUS, max(math.dist(p, (cx, cy)) for p in members))
        circles.append((round(cx, 2), round(cy, 2), round(radius, 2)))
    circles.sort(key=lambda c: math.dist((c[0], c[1]), (pose.x, pose.y)))
    return circles[:max_obstacles]


def _cluster(points: list[tuple[float, float]], gap: float) -> list[list[tuple[float, float]]]:
    """Agrupa por proximidade (ligação simples): dois pontos a menos de `gap` ficam no mesmo grupo."""
    clusters: list[list[tuple[float, float]]] = []
    for point in points:
        near = [c for c in clusters if any(math.dist(point, q) <= gap for q in c)]
        merged = [point]
        for c in near:
            merged += c
            clusters.remove(c)
        clusters.append(merged)
    return clusters
