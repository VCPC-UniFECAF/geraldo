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

test("com a parada ativa o botão passa a desligar e deixa de ser vermelho", () => {
  render(<BotaoEmergencia role="admin" ativo ocupado={false} onAlternar={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Desligar parada de emergência" })).not.toHaveClass("bg-vermelho-500");
});

test("desligar pede confirmação: nada é chamado até Confirmar", async () => {
  const onAlternar = vi.fn();
  render(<BotaoEmergencia role="admin" ativo ocupado={false} onAlternar={onAlternar} />);
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  expect(screen.getByRole("alertdialog")).toHaveTextContent("Desligar a parada de emergência religa o robô. Confirmar?");
  expect(onAlternar).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  expect(onAlternar).toHaveBeenCalledExactlyOnceWith(false);
});

test("Cancelar fecha a confirmação, não chama e devolve o foco ao botão Desligar", async () => {
  const onAlternar = vi.fn();
  render(<BotaoEmergencia role="admin" ativo ocupado={false} onAlternar={onAlternar} />);
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(onAlternar).not.toHaveBeenCalled();
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Desligar parada de emergência" })).toHaveFocus();
});

test("Esc cancela a confirmação pelo teclado e Enter no foco inicial também cancela", async () => {
  const onAlternar = vi.fn();
  render(<BotaoEmergencia role="admin" ativo ocupado={false} onAlternar={onAlternar} />);
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  await userEvent.keyboard("{Enter}");
  expect(onAlternar).not.toHaveBeenCalled();
});

test("acionar continua de um toque, sem confirmação", async () => {
  const onAlternar = vi.fn();
  render(<BotaoEmergencia role="admin" ativo={false} ocupado={false} onAlternar={onAlternar} />);
  await userEvent.click(screen.getByRole("button", { name: "Parada de emergência" }));
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  expect(onAlternar).toHaveBeenCalledWith(true);
});

test("ocupado desabilita o botão", () => {
  render(<BotaoEmergencia role="admin" ativo={false} ocupado onAlternar={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Parada de emergência" })).toBeDisabled();
});

test("se a parada é desligada por fora com o diálogo aberto, ele fecha e não reabre quando a parada volta", async () => {
  const props = { role: "admin" as const, ocupado: false, onAlternar: vi.fn() };
  const { rerender } = render(<BotaoEmergencia {...props} ativo />);
  await userEvent.click(screen.getByRole("button", { name: "Desligar parada de emergência" }));
  rerender(<BotaoEmergencia {...props} ativo={false} />);
  rerender(<BotaoEmergencia {...props} ativo />);
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
});
