import { render, screen } from "@testing-library/react";
import { DELIVERY, LOCATIONS } from "../api/mocks/fixtures";
import { EntregaAdapter } from "../domain/EntregaAdapter";
import { DeliveryQueueRow } from "./DeliveryQueueRow";

const adapter = new EntregaAdapter((id) => LOCATIONS.find((l) => l.id === id)?.name ?? id);
const entrega = adapter.adaptar(DELIVERY);

test("mostra horário, itens, origem e destino, prioridade e status", () => {
  render(
    <ul>
      <DeliveryQueueRow entrega={entrega} />
    </ul>,
  );
  expect(screen.getByText("10:20")).toHaveClass("tabular-nums");
  expect(screen.getByText(/5 × Dipirona 500mg/)).toHaveTextContent("Farmácia central → Consultório 1");
  expect(screen.getByText("Média")).toBeInTheDocument();
  expect(screen.getByText("A caminho")).toBeInTheDocument();
});

test("é uma linha arredondada de fundo claro que quebra em duas linhas no celular", () => {
  render(
    <ul>
      <DeliveryQueueRow entrega={entrega} />
    </ul>,
  );
  expect(screen.getByRole("listitem")).toHaveClass("rounded-controle", "bg-fundo", "flex-col", "md:flex-row");
});
