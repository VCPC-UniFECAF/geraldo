import { DELIVERY, LOCATIONS } from "../api/mocks/fixtures";
import { EntregaAdapter } from "./EntregaAdapter";

const adapter = new EntregaAdapter((id) => LOCATIONS.find((l) => l.id === id)?.name ?? id);

test("traduz o contrato do backend para o modelo da interface", () => {
  expect(adapter.adaptar(DELIVERY)).toEqual({
    id: 1,
    origem: "Farmácia central",
    destino: "Consultório 1",
    itens: [{ nome: "Dipirona 500mg", quantidade: 5 }],
    prioridade: "media",
    status: "EM_ROTA",
    solicitadaEm: new Date("2026-11-09T13:20:00Z"),
  });
});

test("local desconhecido cai no próprio id", () => {
  expect(adapter.adaptar({ ...DELIVERY, dest_id: "sala-x" }).destino).toBe("sala-x");
});
