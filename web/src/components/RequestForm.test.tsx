import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LOCATIONS, STOCK } from "../api/mocks/fixtures";
import { RequestForm } from "./RequestForm";

const loadStock = vi.fn(async (originId: string) => STOCK.filter((s) => s.location_id === originId));

function setup(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  render(<RequestForm locations={LOCATIONS} defaultDestId="consultorio1" loadStock={loadStock} onSubmit={onSubmit} />);
  return onSubmit;
}

beforeEach(() => loadStock.mockClear());

test("carrega o estoque da farmácia e lista só o que tem saldo disponível", async () => {
  setup();
  expect(await screen.findByRole("option", { name: "Dipirona 500 mg (420 disponíveis)" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /Amoxicilina/ })).not.toBeInTheDocument();
  expect(loadStock).toHaveBeenCalledWith("farmacia");
});

test("o destino já vem preenchido com o local do usuário e não oferece locais sem ponto de parada", async () => {
  setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  expect(screen.getByLabelText("Destino")).toHaveValue("consultorio1");
  expect(screen.queryByRole("option", { name: "Recepção" })).not.toBeInTheDocument();
});

test("envia o pedido com a quantidade, o destino padrão e a prioridade média", async () => {
  const onSubmit = setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  const quantity = screen.getByLabelText("Quantidade");
  await userEvent.clear(quantity);
  await userEvent.type(quantity, "5");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(onSubmit).toHaveBeenCalledWith({
    origin_id: "farmacia",
    dest_id: "consultorio1",
    items: [{ item_id: "dipirona-500mg", quantity: 5 }],
    priority: "media",
  });
});

test("quantidade zero mostra o erro e não envia", async () => {
  const onSubmit = setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  const quantity = screen.getByLabelText("Quantidade");
  await userEvent.clear(quantity);
  await userEvent.type(quantity, "0");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Informe uma quantidade maior que zero.");
  expect(onSubmit).not.toHaveBeenCalled();
});

test("origem igual ao destino mostra o erro e não envia", async () => {
  const onSubmit = setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.selectOptions(screen.getByLabelText("Destino"), "farmacia");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Origem e destino precisam ser diferentes.");
  expect(onSubmit).not.toHaveBeenCalled();
});

test("prioridade crítica avisa que exige a assinatura do farmacêutico", async () => {
  setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  expect(screen.queryByText(/assinatura do farmacêutico/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText("Crítica"));
  expect(screen.getByText("Prioridade crítica exige a assinatura do farmacêutico.")).toBeInTheDocument();
});

test("mostra a mensagem de erro devolvida pela API", async () => {
  const onSubmit = vi.fn().mockRejectedValue(new Error("Estoque insuficiente de dipirona-500mg em farmacia."));
  setup(onSubmit);
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Estoque insuficiente de dipirona-500mg em farmacia.");
});
