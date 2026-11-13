import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY, TELEMETRIAS } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { server } from "../api/mocks/server";
import type { Role } from "../api/types";
import { TelemetriaCliente } from "../domain/TelemetriaCliente";
import { fabricaDeSockets } from "../test/SocketFalso";
import { PainelPage } from "./PainelPage";

async function montar(role: Role = "medico") {
  const { criar, sockets } = fabricaDeSockets();
  const telemetria = new TelemetriaCliente(() => "ws://teste/ws/telemetry", criar);
  const api = new HttpApiClient();
  const usuarios: Partial<Record<Role, string>> = { farmaceutico: "farmaceutico1", admin: "admin" };
  if (usuarios[role]) await api.login(usuarios[role]!, "demo");
  render(<PainelPage api={api} telemetria={telemetria} role={role} />);
  return { sockets };
}

const cartaoDoRobo = () => screen.getByRole("region", { name: "Estado do robô" });

test("mostra o estado inicial e depois o que chega pelo WebSocket", async () => {
  const { sockets } = await montar();
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
  const { sockets } = await montar();
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
  await montar();
  const andamento = await screen.findByRole("region", { name: "Em andamento" });
  await waitFor(() => expect(within(andamento).getAllByRole("listitem")).toHaveLength(1));
  const fila = screen.getByRole("region", { name: "Fila de espera" });
  const linhas = within(fila).getAllByRole("listitem");
  expect(linhas).toHaveLength(2);
  expect(linhas[0]).toHaveTextContent("Crítica");
  expect(linhas[1]).toHaveTextContent("Rotina");
});

test("sem entregas mostra os textos de vazio", async () => {
  await montar();
  expect(await screen.findByText("Nenhuma entrega em andamento.")).toBeInTheDocument();
  expect(screen.getByText("Ninguém na fila.")).toBeInTheDocument();
});

test("parada de emergência na telemetria mostra o alerta vermelho", async () => {
  const { sockets } = await montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber(TELEMETRIAS.PARADA_EMERGENCIA);
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Parada de emergência ativa. O robô está parado até a liberação.");
});

test("bateria baixa mostra o alerta", async () => {
  const { sockets } = await montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber({ ...TELEMETRIAS.IDLE, battery: 12 });
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Bateria abaixo de 20%. Evite novos pedidos até a recarga.");
});

test("conexão caída mostra o aviso de reconexão e some quando volta", async () => {
  const { sockets } = await montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => sockets[0].cair());
  expect(screen.getByRole("status")).toHaveTextContent("Sem conexão com o robô. Tentando reconectar…");
});

test("erro ao carregar as entregas aparece como alerta", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
  await montar();
  expect(await screen.findByRole("alert")).toHaveTextContent("Faça login para continuar.");
});

test("médico não vê o botão de emergência", async () => {
  await montar("medico");
  await within(cartaoDoRobo()).findByText("Livre");
  expect(screen.queryByRole("button", { name: /parada de emergência/i })).not.toBeInTheDocument();
});

test("farmacêutico aciona a parada: o corpo é {active: true}, o alerta aparece e o botão vira Desligar", async () => {
  let corpo: unknown = null;
  server.use(
    http.post("http://localhost:8000/robot/estop", async ({ request }) => {
      corpo = await request.json();
      return new HttpResponse(null, { status: 204 });
    }),
  );
  await montar("farmaceutico");
  await within(cartaoDoRobo()).findByText("Livre");
  await userEvent.click(screen.getByRole("button", { name: "Parada de emergência" }));
  expect(await screen.findByRole("button", { name: "Desligar parada de emergência" })).toBeInTheDocument();
  expect(corpo).toEqual({ active: true });
  expect(screen.getByRole("alert")).toHaveTextContent("Parada de emergência ativa. O robô está parado até a liberação.");
});

test("desligar a parada manda {active: false} e o alerta some", async () => {
  const corpos: unknown[] = [];
  server.use(
    http.post("http://localhost:8000/robot/estop", async ({ request }) => {
      corpos.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
  );
  await montar("admin");
  await within(cartaoDoRobo()).findByText("Livre");
  await userEvent.click(screen.getByRole("button", { name: "Parada de emergência" }));
  await userEvent.click(await screen.findByRole("button", { name: "Desligar parada de emergência" }));
  await userEvent.click(await screen.findByRole("button", { name: "Confirmar" }));
  expect(await screen.findByRole("button", { name: "Parada de emergência" })).toBeInTheDocument();
  expect(corpos).toEqual([{ active: true }, { active: false }]);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("parada acionada por outro painel (só a telemetria sabe) também liga o alerta e o botão Desligar", async () => {
  const { sockets } = await montar("farmaceutico");
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber(TELEMETRIAS.PARADA_EMERGENCIA);
  });
  expect(screen.getByRole("button", { name: "Desligar parada de emergência" })).toBeInTheDocument();
});

test("erro da API ao acionar aparece em alerta e o botão volta ao normal", async () => {
  server.use(
    http.post("http://localhost:8000/robot/estop", () =>
      HttpResponse.json({ detail: "Só administrador e farmacêutico acionam a parada de emergência." }, { status: 403 }),
    ),
  );
  await montar("farmaceutico");
  await within(cartaoDoRobo()).findByText("Livre");
  await userEvent.click(screen.getByRole("button", { name: "Parada de emergência" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Só administrador e farmacêutico acionam a parada de emergência.");
  expect(screen.getByRole("button", { name: "Parada de emergência" })).toBeEnabled();
});

test("depois de Desligar (204), se a telemetria segue em PARADA_EMERGENCIA o alerta e o botão Desligar continuam", async () => {
  server.use(http.post("http://localhost:8000/robot/estop", () => new HttpResponse(null, { status: 204 })));
  const { sockets } = await montar("farmaceutico");
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber(TELEMETRIAS.PARADA_EMERGENCIA);
  });
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Confirmar" })).not.toBeInTheDocument());
  act(() => {
    sockets[0].receber(TELEMETRIAS.PARADA_EMERGENCIA);
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Parada de emergência ativa");
  expect(screen.getByRole("button", { name: "Desligar parada de emergência" })).toBeInTheDocument();
});

test("cancelar a confirmação não chama a API; confirmar chama", async () => {
  const corpos: unknown[] = [];
  server.use(
    http.post("http://localhost:8000/robot/estop", async ({ request }) => {
      corpos.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const { sockets } = await montar("admin");
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => {
    sockets[0].receber(TELEMETRIAS.PARADA_EMERGENCIA);
  });
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  expect(screen.getByText("Desligar a parada de emergência religa o robô. Confirmar?")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(corpos).toEqual([]);
  expect(screen.getByRole("button", { name: "Desligar parada de emergência" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  await waitFor(() => expect(corpos).toEqual([{ active: false }]));
});

test("o erro das entregas some quando a recarga seguinte dá certo", async () => {
  let chamadas = 0;
  server.use(
    http.get("http://localhost:8000/deliveries", () => {
      chamadas += 1;
      return chamadas === 1 ? HttpResponse.json({ detail: "Falhou ao carregar." }, { status: 500 }) : HttpResponse.json([]);
    }),
  );
  const { sockets } = await montar();
  expect(await screen.findByRole("alert")).toHaveTextContent("Falhou ao carregar.");
  act(() => {
    sockets[0].receber(TELEMETRIAS.A_CAMINHO);
  });
  await waitFor(() => expect(screen.queryByText("Falhou ao carregar.")).not.toBeInTheDocument());
});

test("o erro da parada some quando a ação seguinte dá certo", async () => {
  let chamadas = 0;
  server.use(
    http.post("http://localhost:8000/robot/estop", () => {
      chamadas += 1;
      return chamadas === 1 ? HttpResponse.json({ detail: "Robô sem resposta." }, { status: 500 }) : new HttpResponse(null, { status: 204 });
    }),
  );
  await montar("farmaceutico");
  await within(cartaoDoRobo()).findByText("Livre");
  await userEvent.click(screen.getByRole("button", { name: "Parada de emergência" }));
  expect(await screen.findByText("Robô sem resposta.")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Parada de emergência" }));
  await waitFor(() => expect(screen.queryByText("Robô sem resposta.")).not.toBeInTheDocument());
});

test("sessão expirada no WebSocket mostra a mensagem em português, sem o aviso de reconexão", async () => {
  const { sockets } = await montar();
  await within(cartaoDoRobo()).findByText("Livre");
  act(() => sockets[0].cair(1008));
  expect(screen.getByRole("alert")).toHaveTextContent("Sua sessão expirou. Entre de novo para ver o robô ao vivo.");
  expect(screen.queryByText(/Tentando reconectar/)).not.toBeInTheDocument();
});

test("desistir de reconectar mostra a mensagem em português", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  try {
    const { sockets } = await montar();
    await within(cartaoDoRobo()).findByText("Livre");
    for (let i = 0; i <= 10; i++) {
      act(() => {
        sockets[i].cair();
        vi.advanceTimersByTime(10000);
      });
    }
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível reconectar ao robô. Recarregue a página.");
  } finally {
    vi.useRealTimers();
  }
});
