import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.obstacles import STATIC_TOLERANCE, Scan, ScanObstacleDetector, StaticMap, detect_obstacles  # noqa: E402
from geraldo_dispatcher.waypoints import Pose  # noqa: E402

HOSPITAL_MAP = ROOT / "robot/ros2_ws/src/geraldo_nav/maps/hospital.yaml"
NEVER = lambda x, y: False  # noqa: E731  (nenhum ponto é parede)
ANGLE_MIN, INCREMENT = -1.5, 3.0 / 359


def scan_with(hits: dict[int, float], beams: int = 360, far: float = math.inf) -> list[float]:
    ranges = [far] * beams
    for index, value in hits.items():
        ranges[index] = value
    return ranges


def beam_at(angle: float) -> int:
    return round((angle - ANGLE_MIN) / INCREMENT)


def detect(ranges, pose=Pose(0.0, 0.0, 0.0), is_static=NEVER, **kwargs):
    return detect_obstacles(ranges, ANGLE_MIN, INCREMENT, pose, is_static, **kwargs)


def test_an_empty_scan_has_no_obstacles():
    assert detect(scan_with({})) == []
    assert detect(scan_with({}, far=12.0)) == []  # retorno no alcance máximo = nada à vista


def test_one_hit_ahead_becomes_a_point_in_front_of_the_sensor():
    (x, y, radius), = detect(scan_with({beam_at(0.0): 2.0}))
    assert x == pytest.approx(2.0, abs=0.01) and y == pytest.approx(0.0, abs=0.02)
    assert radius == 0.10  # raio mínimo


def test_the_sensor_pose_moves_and_turns_the_points_into_the_map_frame():
    sensor = Pose(10.0, 20.0, math.pi / 2)  # olhando para +y
    (x, y, _), = detect(scan_with({beam_at(0.0): 2.0}), pose=sensor)
    assert x == pytest.approx(10.0, abs=0.02) and y == pytest.approx(22.0, abs=0.02)


def test_points_that_match_the_static_map_are_dropped():
    wall = lambda x, y: x > 5.0  # noqa: E731
    ranges = scan_with({beam_at(0.0): 6.0, beam_at(0.5): 1.0})
    obstacles = detect(ranges, is_static=wall)
    assert len(obstacles) == 1 and obstacles[0][0] < 5.0


def test_neighbouring_points_form_one_obstacle_whose_radius_covers_them():
    hits = {i: 3.0 for i in range(beam_at(-0.05), beam_at(0.05) + 1)}  # um objeto de uns 30 cm de largura a 3 m
    (x, y, radius), = detect(scan_with(hits))
    assert x == pytest.approx(3.0, abs=0.05) and y == pytest.approx(0.0, abs=0.05)
    assert 0.1 <= radius <= 0.3


def test_far_apart_objects_stay_separate_and_the_closest_comes_first():
    ranges = scan_with({beam_at(-0.8): 3.0, beam_at(0.0): 1.5, beam_at(0.8): 3.8})
    obstacles = detect(ranges)
    assert len(obstacles) == 3
    distances = [math.hypot(x, y) for x, y, _ in obstacles]
    assert distances == sorted(distances)


def test_only_obstacles_within_4_m_are_reported():
    # longe, 2° de erro do AMCL (medido no Gazebo) já tiram a parede do lugar e ela vira obstáculo fantasma
    assert detect(scan_with({beam_at(0.0): 5.0})) == []
    assert len(detect(scan_with({beam_at(0.0): 3.5}))) == 1


def test_at_most_20_obstacles_are_reported():
    ranges = scan_with({i: 3.0 for i in range(0, 360, 8)})  # 45 pontos a uns 20 cm um do outro
    assert len(detect(ranges, cluster_gap=0.05)) == 20       # com o gap menor que isso nenhum se junta
    assert len(detect(ranges, cluster_gap=0.05, max_obstacles=5)) == 5
    assert len(detect(ranges)) == 1                           # com o gap padrão (35 cm) viram um só


def test_readings_outside_the_sensor_range_are_ignored():
    assert detect(scan_with({10: 0.05, 11: math.nan, 12: 12.0, 13: math.inf})) == []


def test_results_are_rounded_to_centimetres():
    (x, y, radius), = detect(scan_with({beam_at(0.3): 2.123456}))
    assert (x, y, radius) == (round(x, 2), round(y, 2), round(radius, 2))


def test_static_map_loaded_from_the_hospital_files():
    static = StaticMap.from_yaml(HOSPITAL_MAP)
    assert (static.width, static.height, static.resolution) == (920, 600, 0.05)
    assert static.occupied_near(0.05, 15.0, 0.1)           # parede oeste (x = 0)
    assert not static.occupied_near(6.5, 26.5, 0.25)       # a base do robô está livre
    assert not static.occupied_near(23.0, 29.0, 0.25)      # corredor norte, onde a maca é colocada
    assert static.occupied_near(-1.0, 5.0, 0.1)            # fora do mapa não é obstáculo novo


def test_static_map_tolerance_catches_points_just_off_a_wall():
    static = StaticMap.from_yaml(HOSPITAL_MAP)
    assert static.occupied_near(0.25, 15.0, 0.25)
    assert not static.occupied_near(0.6, 15.0, 0.25)


def test_a_toy_map_flips_the_image_so_row_zero_is_the_bottom():
    # 3x2 células, 1 m cada: só a célula (col 2, linha de baixo) ocupada
    static = StaticMap(3, 2, 1.0, (0.0, 0.0), bytes([0, 0, 1, 0, 0, 0]))
    assert static.occupied_near(2.5, 0.5, 0.1) and not static.occupied_near(2.5, 1.5, 0.1)


def test_furniture_rects_count_as_static():
    # o mapa do Nav2 só tem paredes; estantes e balcões ficam de fora e não são obstáculo novo
    static = StaticMap(4, 4, 1.0, (0.0, 0.0), bytes(16)).with_rects([(1.0, 1.0, 2.0, 3.0)])
    assert static.occupied_near(1.5, 2.5, 0.0)
    assert not static.occupied_near(3.5, 0.5, 0.0)


def test_hospital_static_map_knows_the_pharmacy_shelves_and_counter():
    furniture = HOSPITAL_MAP.parent / "furniture.json"
    static = StaticMap.from_yaml(HOSPITAL_MAP).with_rects(json.loads(furniture.read_text(encoding="utf-8")))
    assert static.occupied_near(11.3, 20.1, STATIC_TOLERANCE)  # frente das estantes da farmácia
    assert static.occupied_near(8.18, 25.4, STATIC_TOLERANCE)  # ponta do balcão
    assert not static.occupied_near(6.2, 25.0, STATIC_TOLERANCE)  # corredor livre diante da doca


EMPTY_MAP = StaticMap(600, 600, 0.05, (0.0, 0.0), bytes(600 * 600))  # 30 x 30 m sem nada ocupado


def scan_message(hits: dict[int, float], frame_id: str = "lidar_link", stamp_ns: int = 5_000_000_000) -> Scan:
    return Scan(frame_id, stamp_ns, scan_with(hits), ANGLE_MIN, INCREMENT, range_min=0.12, range_max=12.0)


def test_the_detector_places_the_scan_with_the_sensor_pose_at_the_scan_stamp():
    asked = []

    def sensor_pose_at(frame_id, stamp_ns):
        asked.append((frame_id, stamp_ns))
        return Pose(10.0, 20.0, math.pi / 2)

    detector = ScanObstacleDetector(EMPTY_MAP, sensor_pose_at)
    (x, y, _), = detector.detect(scan_message({beam_at(0.0): 2.0}))
    assert asked == [("lidar_link", 5_000_000_000)]
    assert x == pytest.approx(10.0, abs=0.02) and y == pytest.approx(22.0, abs=0.02)


def test_the_detector_drops_the_scan_when_there_is_no_transform_at_its_stamp():
    # a pose velha de outro instante faria a parede sair do lugar e virar obstáculo: sem TF, sem obstáculo
    detector = ScanObstacleDetector(EMPTY_MAP, lambda frame_id, stamp_ns: None)
    assert detector.detect(scan_message({beam_at(0.0): 2.0})) == []


def test_the_detector_ignores_what_the_static_map_explains():
    wall = StaticMap(40, 40, 0.05, (0.0, 0.0), bytes(1600)).with_rects([(1.9, 0.0, 2.1, 2.0)])  # parede em x = 2
    detector = ScanObstacleDetector(wall, lambda frame_id, stamp_ns: Pose(0.5, 1.0, 0.0))
    assert detector.detect(scan_message({beam_at(0.0): 1.5})) == []
