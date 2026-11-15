import { render, screen } from "@testing-library/react";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY_PENDENTE } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { FarmaciaPage } from "./FarmaciaPage";

async function montar(role: "farmaceutico" | "admin") {
  const api = new HttpApiClient();
  await api.login(role === "admin" ? "admin" : "farmaceutico1", "demo");
  render(<FarmaciaPage api={api} usuario={await api.me()} />);
}

test("a Farmácia tem as Aprovações no topo e o Estoque embaixo", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("farmaceutico");
  expect(screen.getByRole("heading", { level: 1, name: "Farmácia" })).toBeInTheDocument();
  const titulos = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(titulos).toEqual(["Aprovações", "Estoque"]);
  expect(await screen.findByText("Bolsa de sangue O negativo")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "Aprovar entrega 4" })).toBeInTheDocument();
});

test("o admin vê a fila e o estoque, sem botões de aprovar", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("admin");
  expect(await screen.findByText("Bolsa de sangue O negativo")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Aprovar|Recusar/ })).not.toBeInTheDocument();
});
