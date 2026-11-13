import type { Ponto, Telemetry } from "../api/types";

export interface Vista {
  robo: Ponto & { yaw: number };
  rota: Ponto[];
  obstaculos: { x: number; y: number; raio: number }[];
}

const ESCALA_MAXIMA = 40; // px por metro: um robô sozinho não vira um ponto gigante
const RAIO_MINIMO = 3; // px: obstáculo pequeno continua visível

// Função pura: leva metros do mapa para pixels do SVG (no mapa o y cresce para cima; no SVG, para baixo).
export function enquadrar(t: Telemetry, largura: number, altura: number, margem = 16): Vista {
  const rota = t.route ?? [];
  const obstaculos = t.obstacles ?? [];
  const xs = [t.pose.x, ...rota.map((p) => p.x), ...obstaculos.flatMap((o) => [o.x - o.radius, o.x + o.radius])];
  const ys = [t.pose.y, ...rota.map((p) => p.y), ...obstaculos.flatMap((o) => [o.y - o.radius, o.y + o.radius])];
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const larguraUtil = largura - 2 * margem;
  const alturaUtil = altura - 2 * margem;
  const larguraReal = Math.max(...xs) - minX;
  const alturaReal = Math.max(...ys) - minY;
  const escala = Math.min(larguraUtil / Math.max(larguraReal, 1), alturaUtil / Math.max(alturaReal, 1), ESCALA_MAXIMA);
  const folgaX = (larguraUtil - larguraReal * escala) / 2;
  const folgaY = (alturaUtil - alturaReal * escala) / 2;
  const px = (x: number) => margem + folgaX + (x - minX) * escala;
  const py = (y: number) => altura - (margem + folgaY + (y - minY) * escala);
  return {
    robo: { x: px(t.pose.x), y: py(t.pose.y), yaw: t.pose.yaw },
    rota: rota.map((p) => ({ x: px(p.x), y: py(p.y) })),
    obstaculos: obstaculos.map((o) => ({ x: px(o.x), y: py(o.y), raio: Math.max(o.radius * escala, RAIO_MINIMO) })),
  };
}
