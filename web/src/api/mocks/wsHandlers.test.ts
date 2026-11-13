import { TELEMETRIAS } from "./fixtures";
import { server } from "./server";
import { roboSimulado } from "./robo";
import { wsHandlers } from "./wsHandlers";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  server.use(...wsHandlers);
});
afterEach(() => vi.useRealTimers());

function conectar(url = "ws://localhost:8000/ws/telemetry?token=abc") {
  const recebidas: { robot_state: string; route: unknown; obstacles: unknown }[] = [];
  const socket = new WebSocket(url);
  socket.onmessage = (e) => recebidas.push(JSON.parse(String(e.data)));
  return { socket, recebidas };
}

test("conecta mesmo com ?token= e manda logo o estado atual, com o corpo do contrato", async () => {
  const { socket, recebidas } = conectar();
  await vi.waitFor(() => expect(recebidas).toHaveLength(1));
  expect(recebidas[0]).toMatchObject({ robot_state: "IDLE", route: TELEMETRIAS.IDLE.route });
  socket.close();
});

test("a cada segundo avança o roteiro e a parada de emergência do mock vence", async () => {
  const { socket, recebidas } = conectar();
  await vi.waitFor(() => expect(recebidas).toHaveLength(1));
  vi.advanceTimersByTime(8000);
  await vi.waitFor(() => expect(recebidas).toHaveLength(9));
  expect(recebidas.map((r) => r.robot_state).slice(3, 9)).toEqual(["IDLE", "CARREGANDO", "CARREGANDO", "CARREGANDO", "CARREGANDO", "A_CAMINHO"]);
  expect(recebidas[8].obstacles).toEqual(TELEMETRIAS.A_CAMINHO.obstacles);
  roboSimulado.definirEstop(true);
  vi.advanceTimersByTime(1000);
  await vi.waitFor(() => expect(recebidas).toHaveLength(10));
  expect(recebidas[9].robot_state).toBe("PARADA_EMERGENCIA");
  roboSimulado.definirEstop(false);
  vi.advanceTimersByTime(1000);
  await vi.waitFor(() => expect(recebidas).toHaveLength(11));
  expect(recebidas[10].robot_state).not.toBe("PARADA_EMERGENCIA");
  socket.close();
});
