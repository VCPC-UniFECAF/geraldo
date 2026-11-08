import { render, screen } from "@testing-library/react";
import { PriorityBadge } from "./PriorityBadge";

test.each([
  ["critica", "Crítica", ["bg-vermelho-100", "text-vermelho-700"]],
  ["media", "Média", ["bg-azul-100", "text-azul-700"]],
  ["rotina", "Rotina", ["bg-neutro-50", "text-neutro-600"]],
] as const)("prioridade %s mostra %s com as cores do design system", (priority, label, classes) => {
  render(<PriorityBadge priority={priority} />);
  expect(screen.getByText(label)).toHaveClass(...classes, "rounded-full");
});
