import { act, render, screen, waitFor, within } from "@testing-library/react";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY, TELEMETRIAS } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { TelemetriaCliente } from "../domain/TelemetriaCliente";
import { fabricaDeSockets } from "../test/SocketFalso";
import { PainelPage } from "./PainelPage";

function montar() {
  const { criar, sockets } = fabricaDeSockets();
  const telemetria = new TelemetriaCliente(() => "ws://teste/ws/telemetry", criar);
  render(<PainelPage api={new HttpApiClient()} telemetria={telemetria} />);
  return { sockets };
}

const cartaoDoRobo = () => screen.getByRole("region", { name: "Estado do robô" });

test("mostra o estado inicial e depois o que chega pelo WebSocket", async () => {
  const { sockets } = montar();
  expect(screen.getByRole("heading", { name: "Painel do robô" })).toBeInTheDocument();
  expect(await within(cartaoDoRobo()).findByText("Livre")).toBeInTheDocument();
  act(() => {
    sockets[0].abrir();
    sockets[0].receber(TELEMETRIAS.A_CAMINHO);
  });
  expect(within(cartaoDoRobo()).getByText("A caminho")).toBeInTheDocument();
  expect(screen.getByText("x 14,2 m · y 28,9 m")).toBeInTheDocument();
});

test("a entrega em curso aparece no cartão com o nome do destino", async () => {
  semearEntregas([DELIVERY]);
  const { sockets } = montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber({ ...TELEMETRIAS.A_CAMINHO, delivery_id: 1 });
  });
  expect(await within(cartaoDoRobo()).findByText("Entrega #1 · Consultório 1")).toBeInTheDocument();
});

test("separa as entregas em andamento da fila, com a crítica primeiro", async () => {
  semearEntregas([
    DELIVERY,
    { ...DELIVERY, id: 3, status: "NA_FILA", priority: "rotina" },
    { ...DELIVERY, id: 4, status: "NA_FILA", priority: "critica" },
  ]);
  montar();
  const andamento = await screen.findByRole("region", { name: "Em andamento" });
  await waitFor(() => expect(within(andamento).getAllByRole("listitem")).toHaveLength(1));
  const fila = screen.getByRole("region", { name: "Fila de espera" });
  const linhas = within(fila).getAllByRole("listitem");
  expect(linhas).toHaveLength(2);
  expect(linhas[0]).toHaveTextContent("Crítica");
  expect(linhas[1]).toHaveTextContent("Rotina");
});

test("sem entregas mostra os textos de vazio", async () => {
  montar();
  expect(await screen.findByText("Nenhuma entrega em andamento.")).toBeInTheDocument();
  expect(screen.getByText("Ninguém na fila.")).toBeInTheDocument();
});

test("parada de emergência na telemetria mostra o alerta vermelho", async () => {
  const { sockets } = montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber(TELEMETRIAS.PARADA_EMERGENCIA);
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Parada de emergência ativa. O robô está parado até a liberação.");
});

test("bateria baixa mostra o alerta", async () => {
  const { sockets } = montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber({ ...TELEMETRIAS.IDLE, battery: 12 });
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Bateria abaixo de 20%. Evite novos pedidos até a recarga.");
});

test("conexão caída mostra o aviso de reconexão e some quando volta", async () => {
  const { sockets } = montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => sockets[0].cair());
  expect(screen.getByRole("status")).toHaveTextContent("Sem conexão com o robô. Tentando reconectar…");
});

test("erro ao carregar as entregas aparece como alerta", async () => {
  const { server } = await import("../api/mocks/server");
  const { http, HttpResponse } = await import("msw");
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
  montar();
  expect(await screen.findByRole("alert")).toHaveTextContent("Faça login para continuar.");
});
