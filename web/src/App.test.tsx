import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
test("começa no login, entra e mostra a tela de solicitar", async () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "G.E.R.A.L.D.O." })).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByRole("heading", { name: "Solicitar medicamento" })).toBeInTheDocument();
});

test("as outras abas mostram Em breve", async () => {
  render(<App />);
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByRole("heading", { name: "Solicitar medicamento" });
  await userEvent.click(screen.getAllByRole("button", { name: "Estoque" })[0]);
  expect(screen.getByText("Em breve.")).toBeInTheDocument();
});

test("a aba Minhas entregas mostra a lista", async () => {
  render(<App />);
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByRole("heading", { name: "Solicitar medicamento" });
  await userEvent.click(screen.getAllByRole("button", { name: "Minhas entregas" })[0]);
  expect(await screen.findByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
});
