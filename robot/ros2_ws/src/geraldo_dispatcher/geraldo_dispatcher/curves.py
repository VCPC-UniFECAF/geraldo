import math

V_MAX = 3.0       # m/s: velocidade de cruzeiro (a mesma do Nav2)
A_LAT = 1.0       # m/s²: aceleração lateral aceita nas curvas (configurável no nó)
A_BRAKE = 1.5     # m/s²: frenagem planejada até a curva, abaixo dos 2,5 m/s² do suavizador de velocidade do Nav2
V_MIN = 0.3       # m/s: o limite nunca zera o robô
LOOKAHEAD = 10.0  # m do caminho à frente que contam
STEP = 0.5        # m entre os pontos em que a curvatura é medida (o /plan tem ruído a cada 5 cm)


def resample(path_xy: list[tuple[float, float]], step: float = STEP) -> list[tuple[float, float]]:
    """Pontos do caminho espaçados por `step` metros de comprimento de arco; o primeiro ponto é mantido."""
    if not path_xy:
        return []
    out, carried = [path_xy[0]], 0.0
    for (x0, y0), (x1, y1) in zip(path_xy, path_xy[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        while length > 0 and carried + length >= step:
            t = (step - carried) / length
            x0, y0 = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            out.append((x0, y0))
            length -= step - carried
            carried = 0.0
        carried += length
    return out


def curvature(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Curvatura (1/m) do círculo que passa por a, b e c (Menger); 0 se os pontos estão alinhados ou repetidos."""
    ab, bc, ca = math.dist(a, b), math.dist(b, c), math.dist(c, a)
    if min(ab, bc, ca) < 1e-9:
        return 0.0
    area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))  # 2 x a área do triângulo
    return 2 * area2 / (ab * bc * ca)


def curve_speed_limit(path_xy: list[tuple[float, float]], v_max: float = V_MAX, a_lat: float = A_LAT,
                      a_brake: float = A_BRAKE, v_min: float = V_MIN, lookahead: float = LOOKAHEAD,
                      step: float = STEP) -> float:
    """Velocidade máxima (m/s) agora, dada a curvatura do caminho à frente (o primeiro ponto é a posição do robô).

    Em cada ponto a curva permite `sqrt(a_lat / curvatura)`; como o robô precisa de distância para frear,
    o limite agora é o menor `sqrt(v_ponto² + 2 * a_brake * distância até o ponto)` dentro de `lookahead`.
    O resultado fica entre `v_min` e `v_max`.
    """
    points = resample(path_xy, step)
    limit = v_max
    for i in range(1, len(points) - 1):
        distance = i * step
        if distance > lookahead:
            break
        k = curvature(points[i - 1], points[i], points[i + 1])
        if k <= 0:
            continue
        v_curve = max(v_min, min(v_max, math.sqrt(a_lat / k)))
        limit = min(limit, math.sqrt(v_curve ** 2 + 2 * a_brake * distance))
    return max(v_min, min(v_max, limit))


def remaining_path(path_xy: list[tuple[float, float]], x: float, y: float) -> list[tuple[float, float]]:
    """O caminho a partir do ponto mais próximo de (x, y): o plano é refeito a cada 1 s e o robô já andou desde então."""
    if not path_xy:
        return []
    nearest = min(range(len(path_xy)), key=lambda i: math.dist(path_xy[i], (x, y)))
    return path_xy[nearest:]
