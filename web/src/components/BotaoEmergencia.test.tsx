import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BotaoEmergencia } from "./BotaoEmergencia";

test.each(["admin", "farmaceutico"] as const)("o papel %s vê o botão vermelho e aciona a parada", async (papel) => {
  const onAlternar = vi.fn();
  render(<BotaoEmergencia role={papel} ativo={false} ocupado={false} onAlternar={onAlternar} />);
  const botao = screen.getByRole("button", { name: "Parada de emergência" });
  expect(botao).toHaveClass("bg-vermelho-500", "min-h-[52px]");
  await userEvent.click(botao);
  expect(onAlternar).toHaveBeenCalledWith(true);
});

test.each(["medico", "enfermeiro", "robo"] as const)("o papel %s não vê o botão", (papel) => {
  const { container } = render(<BotaoEmergencia role={papel} ativo={false} ocupado={false} onAlternar={vi.fn()} />);
  expect(container).toBeEmptyDOMElement();
});

test("com a parada ativa o botão passa a desligar e deixa de ser vermelho", async () => {
  const onAlternar = vi.fn();
  render(<BotaoEmergencia role="admin" ativo ocupado={false} onAlternar={onAlternar} />);
  const botao = screen.getByRole("button", { name: "Desligar parada de emergência" });
  expect(botao).not.toHaveClass("bg-vermelho-500");
  await userEvent.click(botao);
  expect(onAlternar).toHaveBeenCalledWith(false);
});

test("ocupado desabilita o botão", () => {
  render(<BotaoEmergencia role="admin" ativo={false} ocupado onAlternar={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Parada de emergência" })).toBeDisabled();
});
