import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

test("é um cartão branco com cantos de 16 px, borda fina e sombra do nível 1", () => {
  render(<Card data-testid="card">Conteúdo</Card>);
  expect(screen.getByTestId("card")).toHaveClass("bg-branco", "rounded-card", "border", "border-neutro-100", "shadow-card");
  expect(screen.getByText("Conteúdo")).toBeInTheDocument();
});

test("aceita className extra sem perder o estilo base", () => {
  render(<Card data-testid="card" className="mt-4">x</Card>);
  expect(screen.getByTestId("card")).toHaveClass("mt-4", "rounded-card");
});
