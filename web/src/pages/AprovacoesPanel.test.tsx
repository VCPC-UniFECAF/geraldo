import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY, DELIVERY_PENDENTE } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { server } from "../api/mocks/server";
import { AprovacoesPanel } from "./AprovacoesPanel";

async function montar(role: "farmaceutico" | "admin", intervaloMs?: number) {
  const api = new HttpApiClient();
  await api.login(role === "admin" ? "admin" : "farmaceutico1", "demo");
  render(<AprovacoesPanel api={api} role={role} intervaloMs={intervaloMs} />);
  return api;
}

test("lista só os pedidos pendentes, com itens, origem, destino e horário", async () => {
  semearEntregas([DELIVERY, DELIVERY_PENDENTE]);
  await montar("farmaceutico");
  expect(await screen.findByRole("heading", { name: "Aprovações" })).toBeInTheDocument();
  expect(await screen.findByText(/2 × Bolsa sangue o neg · Banco de sangue → Consultório 1/)).toBeInTheDocument();
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
});

test("sem pedidos pendentes mostra o estado vazio", async () => {
  semearEntregas([DELIVERY]);
  await montar("farmaceutico");
  expect(await screen.findByText("Nenhum pedido crítico esperando a sua assinatura.")).toBeInTheDocument();
});

test("o farmacêutico aprova: o pedido sai da lista e aparece o aviso", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Aprovar entrega 4" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega 4 aprovada. O robô vai buscar assim que estiver livre.");
  await waitFor(() => expect(screen.queryByRole("button", { name: "Aprovar entrega 4" })).not.toBeInTheDocument());
});

test("recusar pede o motivo, valida e só então envia; o pedido sai da lista", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  const api = await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Recusar entrega 4" }));
  const campo = screen.getByLabelText("Motivo da recusa");
  await userEvent.type(campo, "ab");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar recusa" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Escreva o motivo da recusa com 3 a 200 caracteres.");
  expect(await api.deliveries()).toMatchObject([{ status: "PENDENTE_APROVACAO" }]);
  await userEvent.clear(campo);
  await userEvent.type(campo, "  Use a prescrição digital  ");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar recusa" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega 4 recusada. O solicitante verá o motivo.");
  expect(await api.deliveries()).toMatchObject([{ status: "CANCELADA", cancel_reason: "Use a prescrição digital" }]);
  expect(screen.queryByLabelText("Motivo da recusa")).not.toBeInTheDocument();
});

test("cancelar a recusa fecha o campo sem enviar nada", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  const api = await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Recusar entrega 4" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(screen.queryByLabelText("Motivo da recusa")).not.toBeInTheDocument();
  expect(await api.deliveries()).toMatchObject([{ status: "PENDENTE_APROVACAO" }]);
});

test("o admin vê a lista sem botões e com a nota", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("admin");
  expect(await screen.findByText(/2 × Bolsa sangue o neg/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Aprovar|Recusar/ })).not.toBeInTheDocument();
  expect(screen.getByText("Só o farmacêutico aprova ou recusa pedidos críticos.")).toBeInTheDocument();
});

test("erro ao aprovar aparece como alerta e a lista continua", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  server.use(http.post("http://localhost:8000/deliveries/4/approve", () => HttpResponse.json({ detail: "A entrega está NA_FILA e não espera aprovação." }, { status: 409 })));
  await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Aprovar entrega 4" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("A entrega está NA_FILA e não espera aprovação.");
  expect(screen.getByRole("button", { name: "Aprovar entrega 4" })).toBeInTheDocument();
});

test("recarrega a lista sozinha: um pedido novo aparece sem trocar de aba", async () => {
  semearEntregas([]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    await montar("farmaceutico", 5000);
    expect(await screen.findByText("Nenhum pedido crítico esperando a sua assinatura.")).toBeInTheDocument();
    semearEntregas([DELIVERY_PENDENTE]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(await screen.findByRole("button", { name: "Aprovar entrega 4" })).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test("401 na recarga mostra a sessão expirada e mantém a lista", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    await montar("farmaceutico", 5000);
    await screen.findByRole("button", { name: "Aprovar entrega 4" });
    server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await waitFor(() => expect(screen.getByText(/Sua sessão expirou/)).toBeInTheDocument());
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(1);
  } finally {
    vi.useRealTimers();
  }
});
