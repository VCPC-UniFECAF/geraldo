import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tabs } from "./Tabs";

const ABAS = [
  { id: "a", rotulo: "Saldos" },
  { id: "b", rotulo: "Histórico" },
];

test("marca a aba ativa com aria-selected e o sublinhado azul", () => {
  render(<Tabs abas={ABAS} ativa="b" onChange={vi.fn()} rotulo="Seções" />);
  expect(screen.getByRole("tablist", { name: "Seções" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Histórico" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: "Histórico" })).toHaveClass("border-azul-500");
  expect(screen.getByRole("tab", { name: "Saldos" })).toHaveAttribute("aria-selected", "false");
});

test("clicar numa aba avisa o id", async () => {
  const onChange = vi.fn();
  render(<Tabs abas={ABAS} ativa="a" onChange={onChange} rotulo="Seções" />);
  await userEvent.click(screen.getByRole("tab", { name: "Histórico" }));
  expect(onChange).toHaveBeenCalledWith("b");
});

test("as abas têm alvo de toque de 44 px", () => {
  render(<Tabs abas={ABAS} ativa="a" onChange={vi.fn()} rotulo="Seções" />);
  for (const aba of screen.getAllByRole("tab")) expect(aba).toHaveClass("min-h-controle");
});
