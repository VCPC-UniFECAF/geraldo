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
    solicitanteId: 1,
    solicitadaEm: new Date("2026-11-09T13:20:00Z"),
    motivoDaRecusa: null,
  });
});

test("local desconhecido cai no próprio id", () => {
  expect(adapter.adaptar({ ...DELIVERY, dest_id: "sala-x" }).destino).toBe("sala-x");
});

test("a recusa vira motivoDaRecusa; sem recusa é null", () => {
  expect(adapter.adaptar({ ...DELIVERY, status: "CANCELADA", cancel_reason: "Sem justificativa" }).motivoDaRecusa).toBe("Sem justificativa");
  expect(adapter.adaptar(DELIVERY).motivoDaRecusa).toBeNull();
});
