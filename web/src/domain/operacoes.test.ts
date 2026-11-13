import { DELIVERY, LOCATIONS, MOVEMENTS, STOCK } from "../api/mocks/fixtures";
import type { Delivery } from "../api/types";
import { abaixoDoMinimo, abaixoDoMinimoPrimeiro, aguardandoRecebimento, emAndamento, filaDeEspera, filtrarComSaldo, locaisComEstoque, locaisComParada, maisRecentesPrimeiro, rotularEstoque, saldo } from "./operacoes";

test("saldo é quantidade menos reservado", () => {
  expect(saldo(STOCK[0])).toBe(420);
  expect(saldo(STOCK[1])).toBe(0);
});

test("filtrarComSaldo tira o que está todo reservado e não altera a lista original", () => {
  const copia = [...STOCK];
  expect(filtrarComSaldo(STOCK).map((e) => e.item_id)).toEqual(["dipirona-500mg", "bolsa-sangue-o-neg"]);
  expect(STOCK).toEqual(copia);
});

test("rotularEstoque monta o texto de cada opção", () => {
  expect(rotularEstoque([STOCK[0]])).toEqual([{ valor: "dipirona-500mg", rotulo: "Dipirona 500 mg (420 disponíveis)" }]);
});

test("locaisComParada tira a recepção; locaisComEstoque só deixa quem tem estoque", () => {
  expect(locaisComParada(LOCATIONS).map((l) => l.id)).not.toContain("recepcao");
  expect(locaisComEstoque(LOCATIONS).every((l) => l.has_stock && l.waypoint)).toBe(true);
});

test("maisRecentesPrimeiro ordena por data sem mutar a entrada", () => {
  const antiga = { ...DELIVERY, id: 1, created_at: "2026-11-09T08:00:00Z" };
  const nova = { ...DELIVERY, id: 2, created_at: "2026-11-09T12:00:00Z" };
  const entrada = [antiga, nova];
  expect(maisRecentesPrimeiro(entrada).map((d) => d.id)).toEqual([2, 1]);
  expect(entrada.map((d) => d.id)).toEqual([1, 2]);
});

test("aguardandoRecebimento só vale para o status AGUARDANDO_RECEBIMENTO", () => {
  expect(aguardandoRecebimento({ status: "AGUARDANDO_RECEBIMENTO" })).toBe(true);
  expect(aguardandoRecebimento({ status: "EM_ROTA" })).toBe(false);
  expect(aguardandoRecebimento({ status: "ENTREGUE" })).toBe(false);
});

test("abaixoDoMinimo pega só quem tem quantidade menor que o mínimo", () => {
  expect(abaixoDoMinimo(STOCK).map((e) => e.item_id)).toEqual(["bolsa-sangue-o-neg"]);
});

test("abaixoDoMinimoPrimeiro põe os críticos na frente sem alterar a lista original", () => {
  const copia = [...STOCK];
  expect(abaixoDoMinimoPrimeiro(STOCK).map((e) => e.item_id)).toEqual(["bolsa-sangue-o-neg", "dipirona-500mg", "amoxicilina-500mg"]);
  expect(STOCK).toEqual(copia);
});

test("maisRecentesPrimeiro também ordena movimentações", () => {
  const ordenadas = maisRecentesPrimeiro(MOVEMENTS);
  expect(ordenadas.map((m) => m.id)).toEqual([4, 3, 2, 1]);
});

const com = (id: number, status: Delivery["status"], priority: Delivery["priority"] = "media"): Delivery => ({ ...DELIVERY, id, status, priority });

test("emAndamento pega EM_ROTA e AGUARDANDO_RECEBIMENTO", () => {
  const lista = [com(1, "EM_ROTA"), com(2, "NA_FILA"), com(3, "AGUARDANDO_RECEBIMENTO"), com(4, "ENTREGUE")];
  expect(emAndamento(lista).map((d) => d.id)).toEqual([1, 3]);
});

test("filaDeEspera ordena por prioridade e depois por id, sem alterar a entrada", () => {
  const lista = [com(5, "NA_FILA", "rotina"), com(2, "NA_FILA", "media"), com(7, "PENDENTE_APROVACAO", "critica"), com(3, "NA_FILA", "media"), com(9, "EM_ROTA")];
  const copia = [...lista];
  expect(filaDeEspera(lista).map((d) => d.id)).toEqual([7, 2, 3, 5]);
  expect(lista).toEqual(copia);
});
