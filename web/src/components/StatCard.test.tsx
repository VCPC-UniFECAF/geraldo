import { render, screen } from "@testing-library/react";
import { StatCard } from "./StatCard";

test("o cartão de destaque é azul sólido com o número em tabular-nums", () => {
  const { container } = render(<StatCard label="Entregas hoje" value={12} caption="9 concluídas · 2 em curso" />);
  expect(container.firstElementChild).toHaveClass("bg-azul-500", "text-branco", "rounded-card");
  expect(screen.getByText("Entregas hoje")).toBeInTheDocument();
  expect(screen.getByText("12")).toHaveClass("tabular-nums", "font-display", "text-4xl");
  expect(screen.getByText("9 concluídas · 2 em curso")).toBeInTheDocument();
});

test("a variante branca usa fundo branco e borda", () => {
  const { container } = render(<StatCard label="Na fila" value="3" variant="branco" />);
  expect(container.firstElementChild).toHaveClass("bg-branco", "border-neutro-100");
});
