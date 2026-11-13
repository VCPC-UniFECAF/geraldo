import { RoboSimulado } from "./robo";

test("começa parado na base (IDLE)", () => {
  expect(new RoboSimulado().atual().robot_state).toBe("IDLE");
});

test("percorre os estados de uma entrega, quatro passos em cada", () => {
  const robo = new RoboSimulado();
  for (let i = 0; i < 4; i++) robo.avancar();
  expect(robo.atual().robot_state).toBe("CARREGANDO");
  for (let i = 0; i < 4; i++) robo.avancar();
  expect(robo.atual().robot_state).toBe("A_CAMINHO");
});

test("a parada de emergência vence o roteiro até ser desligada", () => {
  const robo = new RoboSimulado();
  robo.definirEstop(true);
  expect(robo.avancar().robot_state).toBe("PARADA_EMERGENCIA");
  robo.definirEstop(false);
  expect(robo.atual().robot_state).not.toBe("PARADA_EMERGENCIA");
});

test("reiniciar volta ao começo", () => {
  const robo = new RoboSimulado();
  for (let i = 0; i < 9; i++) robo.avancar();
  robo.definirEstop(true);
  robo.reiniciar();
  expect(robo.atual().robot_state).toBe("IDLE");
});
