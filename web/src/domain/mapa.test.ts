import type { Telemetry } from "../api/types";
import { enquadrar } from "./mapa";

const base = (parcial: Partial<Telemetry>): Telemetry => ({
  robot_state: "A_CAMINHO",
  pose: { x: 0, y: 0, yaw: 0 },
  battery: 90,
  updated_at: "2026-11-13T12:00:00+00:00",
  ...parcial,
});

test("um robô sozinho fica no centro da área", () => {
  const vista = enquadrar(base({ pose: { x: 6.5, y: 26.5, yaw: 1 } }), 200, 100);
  expect(vista.robo.x).toBeCloseTo(100);
  expect(vista.robo.y).toBeCloseTo(50);
  expect(vista.robo.yaw).toBe(1);
  expect(vista.rota).toEqual([]);
});

test("a rota ocupa a largura útil e o eixo y é invertido para o SVG", () => {
  const vista = enquadrar(base({ route: [{ x: 0, y: 0 }, { x: 10, y: 0 }] }), 200, 100);
  expect(vista.rota[0].x).toBeCloseTo(16);
  expect(vista.rota[1].x).toBeCloseTo(184);
  expect(vista.rota[0].y).toBeCloseTo(50);
  const acima = enquadrar(base({ route: [{ x: 0, y: 0 }, { x: 0, y: 10 }] }), 200, 100);
  expect(acima.rota[1].y).toBeLessThan(acima.rota[0].y);
});

test("o obstáculo ganha raio em pixels na mesma escala", () => {
  const vista = enquadrar(base({ obstacles: [{ x: 4, y: 0, radius: 1 }] }), 200, 100);
  expect(vista.robo.x).toBeCloseTo(16);
  expect(vista.robo.y).toBeCloseTo(50);
  expect(vista.obstaculos[0].x).toBeCloseTo(150.4);
  expect(vista.obstaculos[0].raio).toBeCloseTo(33.6);
});

test("obstáculo muito pequeno não some: raio mínimo de 3 px", () => {
  const vista = enquadrar(base({ route: [{ x: 0, y: 0 }, { x: 100, y: 0 }], obstacles: [{ x: 50, y: 0, radius: 0.01 }] }), 200, 100);
  expect(vista.obstaculos[0].raio).toBe(3);
});
