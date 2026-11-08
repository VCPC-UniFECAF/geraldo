import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpApiClient } from "../api/HttpApiClient";
import { SolicitarPage } from "./SolicitarPage";

test("carrega o usuário e os locais, envia o pedido e confirma", async () => {
  render(<SolicitarPage api={new HttpApiClient()} />);
  expect(await screen.findByRole("heading", { name: "Solicitar medicamento" })).toBeInTheDocument();
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega solicitada. Acompanhe em Minhas entregas.");
});
