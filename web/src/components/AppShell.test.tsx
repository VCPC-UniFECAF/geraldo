import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "./AppShell";

test("tem a barra lateral (desktop) e a barra inferior (celular) com os mesmos itens", () => {
  render(
    <AppShell active="solicitar" role="farmaceutico" onNavigate={vi.fn()}>
      <p>conteúdo</p>
    </AppShell>,
  );
  const navs = screen.getAllByRole("navigation");
  expect(navs).toHaveLength(2);
  expect(navs[0]).toHaveClass("hidden", "md:flex");
  expect(navs[1]).toHaveClass("md:hidden");
  expect(screen.getAllByRole("button", { name: "Solicitar" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Minhas entregas" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Farmácia" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Painel" })).toHaveLength(2);
  expect(screen.getByText("conteúdo")).toBeInTheDocument();
});

test("marca a página ativa com aria-current", () => {
  render(
    <AppShell active="entregas" role="farmaceutico" onNavigate={vi.fn()}>
      x
    </AppShell>,
  );
  for (const button of screen.getAllByRole("button", { name: "Minhas entregas" })) {
    expect(button).toHaveAttribute("aria-current", "page");
  }
  for (const button of screen.getAllByRole("button", { name: "Solicitar" })) {
    expect(button).not.toHaveAttribute("aria-current");
  }
});

test("clicar num item navega", async () => {
  const onNavigate = vi.fn();
  render(
    <AppShell active="solicitar" role="farmaceutico" onNavigate={onNavigate}>
      x
    </AppShell>,
  );
  await userEvent.click(screen.getAllByRole("button", { name: "Farmácia" })[0]);
  expect(onNavigate).toHaveBeenCalledWith("farmacia");
});

test("os botões de navegação têm alvo de toque de 44 px", () => {
  render(
    <AppShell active="solicitar" role="farmaceutico" onNavigate={vi.fn()}>
      x
    </AppShell>,
  );
  for (const button of screen.getAllByRole("button")) expect(button).toHaveClass("min-h-controle");
});

test("clicar em Painel navega para o painel", async () => {
  const onNavigate = vi.fn();
  render(
    <AppShell active="solicitar" role="farmaceutico" onNavigate={onNavigate}>
      x
    </AppShell>,
  );
  await userEvent.click(screen.getAllByRole("button", { name: "Painel" })[0]);
  expect(onNavigate).toHaveBeenCalledWith("painel");
});

test("médico e enfermeiro não veem a aba Farmácia; farmacêutico e admin veem", () => {
  const { rerender } = render(<AppShell active="solicitar" role="medico" onNavigate={vi.fn()}>x</AppShell>);
  expect(screen.queryByRole("button", { name: "Farmácia" })).not.toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Painel" })).toHaveLength(2);
  rerender(<AppShell active="solicitar" role="enfermeiro" onNavigate={vi.fn()}>x</AppShell>);
  expect(screen.queryByRole("button", { name: "Farmácia" })).not.toBeInTheDocument();
  for (const role of ["farmaceutico", "admin"] as const) {
    rerender(<AppShell active="solicitar" role={role} onNavigate={vi.fn()}>x</AppShell>);
    expect(screen.getAllByRole("button", { name: "Farmácia" })).toHaveLength(2);
  }
});
