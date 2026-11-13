import { TELEMETRIAS } from "../api/mocks/fixtures";
import { atrasoDeReconexao, bateriaBaixa, comprimentoDaRota, lerTelemetria, segundosAteChegar, semSinal } from "./telemetria";

test("lerTelemetria aceita o corpo do contrato", () => {
  expect(lerTelemetria(JSON.stringify(TELEMETRIAS.IDLE))).toEqual(TELEMETRIAS.IDLE);
  expect(lerTelemetria(JSON.stringify(TELEMETRIAS.A_CAMINHO))?.route).toHaveLength(3);
});

test("lerTelemetria preenche o que o contrato deixa opcional", () => {
  const corpo = { robot_state: "IDLE", pose: { x: 1, y: 2, yaw: 0 }, battery: 50, updated_at: "2026-11-13T12:00:00+00:00" };
  expect(lerTelemetria(JSON.stringify(corpo))).toEqual({ ...corpo, delivery_id: null, route: [], obstacles: [] });
});

test.each([
  ["texto que não é JSON", "oi"],
  ["JSON que não é objeto", "42"],
  ["estado fora do enum", JSON.stringify({ ...TELEMETRIAS.IDLE, robot_state: "VOANDO" })],
  ["pose incompleta", JSON.stringify({ ...TELEMETRIAS.IDLE, pose: { x: 1 } })],
  ["bateria que não é número", JSON.stringify({ ...TELEMETRIAS.IDLE, battery: "cheia" })],
])("lerTelemetria recusa %s", (_nome, texto) => {
  expect(lerTelemetria(texto)).toBeNull();
});

test("atrasoDeReconexao dobra a cada tentativa até 10 s", () => {
  expect([0, 1, 2, 3, 4, 9].map(atrasoDeReconexao)).toEqual([1000, 2000, 4000, 8000, 10000, 10000]);
});

test("comprimentoDaRota soma os trechos em metros", () => {
  expect(comprimentoDaRota([])).toBe(0);
  expect(comprimentoDaRota([{ x: 0, y: 0 }, { x: 3, y: 4 }, { x: 3, y: 10 }])).toBe(11);
});

test("segundosAteChegar usa 3 m/s e arredonda para cima; sem rota não há estimativa", () => {
  expect(segundosAteChegar(TELEMETRIAS.A_CAMINHO.route)).toBe(5);
  expect(segundosAteChegar([{ x: 0, y: 0 }, { x: 30, y: 0 }])).toBe(10);
  expect(segundosAteChegar([])).toBeNull();
  expect(segundosAteChegar(undefined)).toBeNull();
});

test("bateriaBaixa vale abaixo de 20", () => {
  expect(bateriaBaixa(19.9)).toBe(true);
  expect(bateriaBaixa(20)).toBe(false);
});

describe("semSinal", () => {
  const agora = Date.parse("2026-11-13T12:00:30+00:00");
  const com = (updated_at: string) => ({ ...TELEMETRIAS.IDLE, updated_at });

  test("telemetria de agora tem sinal", () => {
    expect(semSinal(com("2026-11-13T12:00:25+00:00"), agora)).toBe(false);
  });
  test("mais velha que o limite não tem sinal, e o limite é injetável", () => {
    expect(semSinal(com("2026-11-13T12:00:00+00:00"), agora)).toBe(true);
    expect(semSinal(com("2026-11-13T12:00:00+00:00"), agora, 60_000)).toBe(false);
  });
  test("o corpo de antes do primeiro POST do robô (1970) e datas inválidas não têm sinal", () => {
    expect(semSinal(com("1970-01-01T00:00:00+00:00"), agora)).toBe(true);
    expect(semSinal(com(""), agora)).toBe(true);
    expect(semSinal(com("ontem"), agora)).toBe(true);
  });
});
