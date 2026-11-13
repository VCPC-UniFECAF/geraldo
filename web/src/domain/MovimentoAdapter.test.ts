import { LOCATIONS, MOVEMENTS, STOCK } from "../api/mocks/fixtures";
import { MovimentoAdapter } from "./MovimentoAdapter";

const adapter = new MovimentoAdapter(
  (id) => LOCATIONS.find((l) => l.id === id)?.name ?? id,
  (id) => STOCK.find((e) => e.item_id === id)?.item_name ?? id,
);

test("traduz o contrato do backend para o modelo da interface", () => {
  expect(adapter.adaptar(MOVEMENTS[1])).toEqual({
    id: 2,
    quando: new Date("2026-11-09T13:22:00Z"),
    tipo: "BAIXA",
    item: "Dipirona 500 mg",
    quantidade: 5,
    local: "Farmácia central",
    entregaId: 1,
  });
});

test("movimentação sem entrega fica com entregaId null", () => {
  const { delivery_id: _ignorado, ...semEntrega } = MOVEMENTS[0];
  expect(adapter.adaptar(semEntrega).entregaId).toBeNull();
});
