import { render, screen } from "@testing-library/react";
import { AlertBanner } from "./AlertBanner";

test("a variante perigo é vermelha, tem ícone e role alert", () => {
  render(<AlertBanner>Corredor norte bloqueado.</AlertBanner>);
  const aviso = screen.getByRole("alert");
  expect(aviso).toHaveTextContent("Corredor norte bloqueado.");
  expect(aviso).toHaveClass("bg-vermelho-50", "border-vermelho-200", "text-vermelho-600", "rounded-controle");
  expect(aviso.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
});

test("a variante info é azul e tem role status", () => {
  render(<AlertBanner variante="info">Reconectando…</AlertBanner>);
  const aviso = screen.getByRole("status");
  expect(aviso).toHaveClass("bg-azul-50", "border-azul-200", "text-azul-700");
});
