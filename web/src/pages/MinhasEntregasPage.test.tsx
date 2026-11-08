import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY } from "../api/mocks/fixtures";
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
