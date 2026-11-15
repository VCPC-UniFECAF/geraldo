"""Conversões puras entre mensagens ROS (lidas por atributo) e os dicts da API da ponte. Não importa rclpy."""
import math

LIDAR_OFFSET = (0.275, 0.0)  # lidar_link em relação ao base_link, em metros (geraldo.urdf.xacro)
RANGE_NAMES = ("front_c", "front_l45", "front_r45", "rear_l135", "rear_r135")
MAX_ROUTE_POINTS = 100
MAX_SCAN_POINTS = 360


def yaw_from_quaternion(z: float, w: float) -> float:
    """Yaw (radianos) de uma rotação em torno de Z."""
    return math.atan2(2 * w * z, 1 - 2 * z * z)


def pose_from_amcl(msg) -> dict:
    p = msg.pose.pose
    yaw = yaw_from_quaternion(p.orientation.z, p.orientation.w)
    return {"x": round(p.position.x, 3), "y": round(p.position.y, 3), "yaw": round(yaw, 3)}


def _evenly(items: list, limit: int) -> list:
    """No máximo `limit` itens espaçados por igual, sempre com o primeiro e o último."""
    if len(items) <= limit:
        return list(items)
    step = (len(items) - 1) / (limit - 1)
    return [items[round(i * step)] for i in range(limit)]


def route_from_path(msg, limit: int = MAX_ROUTE_POINTS) -> list[dict]:
    points = [(s.pose.position.x, s.pose.position.y) for s in msg.poses]
    return [{"x": round(x, 3), "y": round(y, 3)} for x, y in _evenly(points, limit)]


def battery_percent(msg) -> float:
    return round(msg.percentage * 100, 1)


def scan_to_dict(msg) -> dict:
    return {
        "angle_min": msg.angle_min,
        "angle_increment": msg.angle_increment,
        "range_min": msg.range_min,
        "range_max": msg.range_max,
        "ranges": list(msg.ranges),
    }


def _hits(scan: dict):
    """(índice, distância) dos feixes que acertaram algo: finitos e dentro do alcance do sensor."""
    for i, r in enumerate(scan["ranges"]):
        if math.isfinite(r) and scan["range_min"] <= r < scan["range_max"]:
            yield i, r


def closest_range(scan: dict) -> float | None:
    """Menor distância medida (metros, 2 casas) ou None se nenhum feixe acertou nada."""
    distances = [r for _, r in _hits(scan)]
    return round(min(distances), 2) if distances else None


def scan_to_map_points(scan: dict, pose: dict, limit: int = MAX_SCAN_POINTS) -> list[dict]:
    """Acertos do LiDAR no referencial `map`, calculados pela pose do AMCL (sem consultar o tf)."""
    cos_y, sin_y = math.cos(pose["yaw"]), math.sin(pose["yaw"])
    ox, oy = LIDAR_OFFSET
    lidar_x = pose["x"] + ox * cos_y - oy * sin_y
    lidar_y = pose["y"] + ox * sin_y + oy * cos_y
    points = []
    for i, r in _hits(scan):
        angle = pose["yaw"] + scan["angle_min"] + i * scan["angle_increment"]
        points.append((lidar_x + r * math.cos(angle), lidar_y + r * math.sin(angle)))
    return [{"x": round(x, 2), "y": round(y, 2)} for x, y in _evenly(points, limit)]
