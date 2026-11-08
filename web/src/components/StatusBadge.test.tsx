import { render, screen } from "@testing-library/react";
import type { DeliveryStatus } from "../api/types";
import { StatusBadge } from "./StatusBadge";

const CASES: [DeliveryStatus, string, string][] = [
  ["PENDENTE_APROVACAO", "Aguardando aprovação", "bg-aviso-50"],
  ["NA_FILA", "Na fila", "bg-neutro-50"],
  ["EM_ROTA", "A caminho", "bg-azul-100"],
  ["AGUARDANDO_RECEBIMENTO", "Aguardando recebimento", "bg-azul-100"],
  ["ENTREGUE", "Entregue", "bg-sucesso-50"],
  ["CANCELADA", "Cancelada", "bg-neutro-50"],
  ["FALHOU", "Falhou", "bg-vermelho-100"],
];

test.each(CASES)("%s mostra %s com texto e ícone (nunca só cor)", (status, label, bg) => {
  const { container } = render(<StatusBadge status={status} />);
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(container.firstElementChild).toHaveClass(bg);
  expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
});

test("cancelada aparece riscada", () => {
  render(<StatusBadge status="CANCELADA" />);
  expect(screen.getByText("Cancelada")).toHaveClass("line-through");
});
