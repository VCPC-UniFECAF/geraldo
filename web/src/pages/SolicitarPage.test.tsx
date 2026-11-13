import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { STOCK } from "../api/mocks/fixtures";
import { server } from "../api/mocks/server";
import { SolicitarPage } from "./SolicitarPage";

test("carrega o usuário e os locais, envia o pedido e confirma", async () => {
  render(<SolicitarPage api={new HttpApiClient()} />);
  expect(await screen.findByRole("heading", { name: "Solicitar medicamento" })).toBeInTheDocument();
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega solicitada. Acompanhe em Minhas entregas.");
});

test("depois de solicitar, o seletor mostra o disponível atualizado", async () => {
  let reservado = 0;
  server.use(
    http.get("http://localhost:8000/stock", () => HttpResponse.json(STOCK.map((s) => ({ ...s, reserved: s.item_id === "dipirona-500mg" ? reservado : s.reserved })))),
    http.post("http://localhost:8000/deliveries", () => {
      reservado = 5;
      return HttpResponse.json({ id: 1 }, { status: 201 });
    }),
  );
  render(<SolicitarPage api={new HttpApiClient()} />);
  await screen.findByRole("option", { name: "Dipirona 500 mg (420 disponíveis)" });
  await userEvent.clear(screen.getByLabelText("Quantidade"));
  await userEvent.type(screen.getByLabelText("Quantidade"), "5");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(await screen.findByRole("option", { name: "Dipirona 500 mg (415 disponíveis)" })).toBeInTheDocument();
});
