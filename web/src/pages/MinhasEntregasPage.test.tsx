import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY, DELIVERY_AGUARDANDO } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { server } from "../api/mocks/server";
import { MinhasEntregasPage } from "./MinhasEntregasPage";

test("lista as entregas do usuário com os nomes dos locais", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json([DELIVERY])));
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
  expect(await screen.findByText(/Farmácia central → Consultório 1/)).toBeInTheDocument();
  expect(screen.getByText("A caminho")).toBeInTheDocument();
});

test("sem entregas mostra o estado vazio e leva para o formulário", async () => {
  const onRequest = vi.fn();
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={onRequest} />);
  expect(await screen.findByText("Nenhuma entrega ainda")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(onRequest).toHaveBeenCalledTimes(1);
});

test("erro da API aparece como alerta", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Faça login para continuar.");
});

test("só a entrega aguardando recebimento tem o botão Confirmar recebimento", async () => {
  semearEntregas([DELIVERY, DELIVERY_AGUARDANDO]);
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  expect(await screen.findAllByRole("listitem")).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: /Confirmar recebimento/ })).toHaveLength(1);
});

test("confirmar o recebimento mostra o aviso e a entrega vira Entregue", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: /Confirmar recebimento/ }));
  expect(await screen.findByRole("status")).toHaveTextContent("Recebimento confirmado. A tampa do robô foi liberada.");
  expect(await screen.findByText("Entregue")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Confirmar recebimento/ })).not.toBeInTheDocument();
});

test("erro ao confirmar aparece como alerta e a lista continua na tela", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  server.use(
    http.post("http://localhost:8000/deliveries/2/confirm-receipt", () =>
      HttpResponse.json({ detail: "Só quem solicitou a entrega confirma o recebimento." }, { status: 403 }),
    ),
  );
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: /Confirmar recebimento/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Só quem solicitou a entrega confirma o recebimento.");
  expect(screen.getByRole("button", { name: /Confirmar recebimento/ })).toBeEnabled();
});

test("se o recarregamento falhar depois de confirmar, mostra o sucesso e o erro da lista à parte", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  let chamadas = 0;
  server.use(
    http.get("http://localhost:8000/deliveries", () => {
      chamadas += 1;
      return chamadas === 1
        ? HttpResponse.json([DELIVERY_AGUARDANDO])
        : HttpResponse.json({ detail: "Não foi possível carregar as entregas." }, { status: 500 });
    }),
  );
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: /Confirmar recebimento/ }));
  expect(await screen.findByRole("status")).toHaveTextContent("Recebimento confirmado.");
  expect(await screen.findByRole("alert")).toHaveTextContent("Recebimento confirmado, mas a lista não atualizou");
  expect(screen.getByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
});

test("enquanto uma confirmação está em andamento todos os botões ficam desabilitados", async () => {
  semearEntregas([DELIVERY_AGUARDANDO, { ...DELIVERY_AGUARDANDO, id: 5 }]);
  let liberar: () => void = () => {};
  const portao = new Promise<void>((r) => (liberar = r));
  server.use(
    http.post("http://localhost:8000/deliveries/:id/confirm-receipt", async () => {
      await portao;
      return HttpResponse.json({});
    }),
  );
  render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  const botoes = await screen.findAllByRole("button", { name: /Confirmar recebimento/ });
  await userEvent.click(botoes[0]);
  for (const b of screen.getAllByRole("button", { name: /Confirmar recebimento/ })) expect(b).toBeDisabled();
  liberar();
});
