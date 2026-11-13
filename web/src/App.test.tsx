import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { TelemetriaCliente } from "./domain/TelemetriaCliente";
import { fabricaDeSockets } from "./test/SocketFalso";

async function entrar(usuario: string) {
  await userEvent.type(screen.getByLabelText("Usuário"), usuario);
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByRole("heading", { name: "Solicitar medicamento" });
}

function montar() {
  const { criar, sockets } = fabricaDeSockets();
  const telemetria = new TelemetriaCliente(() => "ws://teste/ws/telemetry", criar);
  render(<App telemetria={telemetria} />);
  return { sockets };
}

test("começa no login, entra e mostra a tela de solicitar", async () => {
  montar();
  expect(screen.getByRole("heading", { name: "G.E.R.A.L.D.O." })).toBeInTheDocument();
  await entrar("medico1");
});

test("a aba Estoque mostra os saldos", async () => {
  montar();
  await entrar("medico1");
  await userEvent.click(screen.getAllByRole("button", { name: "Estoque" })[0]);
  expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
  expect(await screen.findByText("Bolsa de sangue O negativo")).toBeInTheDocument();
});

test("a aba Minhas entregas mostra a lista", async () => {
  montar();
  await entrar("medico1");
  await userEvent.click(screen.getAllByRole("button", { name: "Minhas entregas" })[0]);
  expect(await screen.findByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
});

test("o médico abre o Painel e não vê o botão de emergência", async () => {
  const { sockets } = montar();
  await entrar("medico1");
  await userEvent.click(screen.getAllByRole("button", { name: "Painel" })[0]);
  expect(await screen.findByRole("heading", { name: "Painel do robô" })).toBeInTheDocument();
  expect(sockets).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Parada de emergência" })).not.toBeInTheDocument();
});

test("o farmacêutico vê o botão de emergência no Painel", async () => {
  montar();
  await entrar("farmaceutico1");
  await userEvent.click(screen.getAllByRole("button", { name: "Painel" })[0]);
  expect(await screen.findByRole("button", { name: "Parada de emergência" })).toBeInTheDocument();
});

test("sair do Painel fecha o WebSocket", async () => {
  const { sockets } = montar();
  await entrar("medico1");
  await userEvent.click(screen.getAllByRole("button", { name: "Painel" })[0]);
  await screen.findByRole("heading", { name: "Painel do robô" });
  await userEvent.click(screen.getAllByRole("button", { name: "Estoque" })[0]);
  expect(sockets[0].fechado).toBe(true);
});
