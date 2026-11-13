import { act, renderHook, waitFor } from "@testing-library/react";
import { TELEMETRIAS } from "../api/mocks/fixtures";
import { TelemetriaCliente } from "../domain/TelemetriaCliente";
import { fabricaDeSockets } from "../test/SocketFalso";
import { useTelemetria } from "./useTelemetria";

function montar(snapshot = () => Promise.resolve(TELEMETRIAS.IDLE)) {
  const { criar, sockets } = fabricaDeSockets();
  const cliente = new TelemetriaCliente(() => "ws://teste", criar);
  const resultado = renderHook(() => useTelemetria(cliente, snapshot));
  return { ...resultado, sockets };
}

test("começa sem dados, pega o primeiro estado pelo snapshot e inicia o WebSocket", async () => {
  const { result, sockets } = montar();
  expect(result.current.telemetria).toBeNull();
  expect(sockets).toHaveLength(1);
  await waitFor(() => expect(result.current.telemetria?.robot_state).toBe("IDLE"));
});

test("as mensagens do WebSocket atualizam a telemetria e a conexão", async () => {
  const { result, sockets } = montar();
  await waitFor(() => expect(result.current.telemetria?.robot_state).toBe("IDLE"));
  act(() => {
    sockets[0].abrir();
    sockets[0].receber(TELEMETRIAS.A_CAMINHO);
  });
  expect(result.current.conexao).toBe("conectado");
  expect(result.current.telemetria?.robot_state).toBe("A_CAMINHO");
});

test("o snapshot que chega depois do WebSocket não sobrescreve o dado mais novo", async () => {
  let resolver: (t: typeof TELEMETRIAS.IDLE) => void = () => {};
  const { result, sockets } = montar(() => new Promise((r) => (resolver = r)));
  act(() => {
    sockets[0].abrir();
    sockets[0].receber(TELEMETRIAS.A_CAMINHO);
  });
  await act(async () => resolver(TELEMETRIAS.IDLE));
  expect(result.current.telemetria?.robot_state).toBe("A_CAMINHO");
});

test("sem snapshot (erro) o hook continua esperando o WebSocket", async () => {
  const { result, sockets } = montar(() => Promise.reject(new Error("sem telemetria ainda")));
  act(() => {
    sockets[0].abrir();
    sockets[0].receber(TELEMETRIAS.CHEGOU);
  });
  expect(result.current.telemetria?.robot_state).toBe("CHEGOU");
});

test("ao desmontar fecha o socket", () => {
  const { unmount, sockets } = montar();
  unmount();
  expect(sockets[0].fechado).toBe(true);
});
