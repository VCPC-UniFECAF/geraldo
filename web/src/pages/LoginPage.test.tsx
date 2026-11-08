import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpApiClient } from "../api/HttpApiClient";
import { Sessao, type EventoSessao } from "../domain/Sessao";
import { LoginPage } from "./LoginPage";

function setup() {
  const sessao = new Sessao(new HttpApiClient());
  const eventos: EventoSessao[] = [];
  sessao.adicionarObserver({ atualizar: (e) => eventos.push(e) });
  render(<LoginPage sessao={sessao} />);
  return eventos;
}

test("entra com usuário e senha corretos e a sessão avisa os observers", async () => {
  const eventos = setup();
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await vi.waitFor(() => expect(eventos).toEqual([{ tipo: "entrou", token: "token-de-teste" }]));
});

test("senha errada mostra a mensagem da API e não entra", async () => {
  const eventos = setup();
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "errada");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Usuário ou senha incorretos. Tente de novo.");
  expect(eventos).toEqual([]);
});
