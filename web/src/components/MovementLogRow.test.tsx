import { render, screen } from "@testing-library/react";
import { LOCATIONS, MOVEMENTS, STOCK } from "../api/mocks/fixtures";
import { MovimentoAdapter } from "../domain/MovimentoAdapter";
import { MovementLogRow } from "./MovementLogRow";

const adapter = new MovimentoAdapter(
  (id) => LOCATIONS.find((l) => l.id === id)?.name ?? id,
  (id) => STOCK.find((e) => e.item_id === id)?.item_name ?? id,
);

function mostrar(indice: number) {
  render(
    <ul>
      <MovementLogRow movimento={adapter.adaptar(MOVEMENTS[indice])} />
    </ul>,
  );
  return screen.getByRole("listitem");
}

test("mostra data e hora, tipo, item, local, entrega e a quantidade com sinal", () => {
  const linha = mostrar(1);
  expect(screen.getByText("09/11 10:22")).toHaveClass("tabular-nums");
  expect(screen.getByText("Baixa")).toBeInTheDocument();
  expect(linha).toHaveTextContent("Dipirona 500 mg · Farmácia central · Entrega #1");
  expect(screen.getByText("-5")).toHaveClass("tabular-nums");
});

test("crédito e estorno têm sinal de mais", () => {
  mostrar(2);
  expect(screen.getByText("+5")).toBeInTheDocument();
  expect(screen.getByText("Crédito")).toBeInTheDocument();
});

test("é uma linha arredondada de fundo claro que quebra em duas linhas no celular", () => {
  expect(mostrar(0)).toHaveClass("rounded-controle", "bg-fundo", "flex-col", "md:flex-row");
});

test("tipo desconhecido não derruba a linha", () => {
  render(<ul><MovementLogRow movimento={{ id: 9, tipo: "NOVO_TIPO" as never, item: "X", local: "Y", entregaId: null, quantidade: 1, quando: new Date("2026-11-09T13:20:00Z") }} /></ul>);
  expect(screen.getByText("Movimentação")).toBeInTheDocument();
});
