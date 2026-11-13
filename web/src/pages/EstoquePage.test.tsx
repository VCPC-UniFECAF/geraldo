import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpApiClient } from "../api/HttpApiClient";
import { EstoquePage } from "./EstoquePage";

test("lista o estoque com o que está abaixo do mínimo primeiro e avisa", async () => {
  render(<EstoquePage api={new HttpApiClient()} />);
  expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
  expect(await screen.findByRole("alert")).toHaveTextContent("1 item abaixo do mínimo. Peça a reposição à farmácia.");
  const itens = await screen.findAllByRole("listitem");
  expect(itens).toHaveLength(3);
  expect(itens[0]).toHaveTextContent("Bolsa de sangue O negativo");
  expect(itens[0]).toHaveTextContent("Banco de sangue");
  expect(itens[0]).toHaveTextContent("Abaixo do mínimo");
});

test("filtrar por local mostra só o estoque daquele local e some o aviso", async () => {
  render(<EstoquePage api={new HttpApiClient()} />);
  await screen.findByRole("option", { name: "Farmácia central" });
  await userEvent.selectOptions(screen.getByLabelText("Local"), "farmacia");
  await waitFor(() => expect(screen.queryByText("Bolsa de sangue O negativo")).not.toBeInTheDocument());
  expect(screen.getByText("Dipirona 500 mg")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("local sem itens mostra a mensagem de vazio", async () => {
  render(<EstoquePage api={new HttpApiClient()} />);
  await screen.findByRole("option", { name: "Consultório 1" });
  await userEvent.selectOptions(screen.getByLabelText("Local"), "consultorio1");
  expect(await screen.findByText("Nenhum item neste local.")).toBeInTheDocument();
});

test("a aba Histórico lista as movimentações, a mais recente primeiro", async () => {
  render(<EstoquePage api={new HttpApiClient()} />);
  await userEvent.click(await screen.findByRole("tab", { name: "Histórico" }));
  const linhas = await screen.findAllByRole("listitem");
  expect(linhas).toHaveLength(4);
  expect(linhas[0]).toHaveTextContent("Estorno");
  expect(linhas[0]).toHaveTextContent("Bolsa de sangue O negativo · Banco de sangue · Entrega #3");
  expect(linhas[3]).toHaveTextContent("Reserva");
});

test("voltar para a aba Saldos mostra o estoque de novo", async () => {
  render(<EstoquePage api={new HttpApiClient()} />);
  await userEvent.click(await screen.findByRole("tab", { name: "Histórico" }));
  await screen.findAllByRole("listitem");
  await userEvent.click(screen.getByRole("tab", { name: "Saldos" }));
  expect(await screen.findByLabelText("Local")).toBeInTheDocument();
});

test("o conteúdo fica num tabpanel ligado à aba ativa", async () => {
  render(<EstoquePage api={new HttpApiClient()} />);
  const aba = await screen.findByRole("tab", { name: "Saldos" });
  const painel = await screen.findByRole("tabpanel");
  expect(painel).toHaveAttribute("id", aba.getAttribute("aria-controls"));
  expect(painel).toHaveAccessibleName("Saldos");
});
