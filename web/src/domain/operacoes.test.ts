import { DELIVERY, LOCATIONS, STOCK } from "../api/mocks/fixtures";
import { abaixoDoMinimo, abaixoDoMinimoPrimeiro, aguardandoRecebimento, filtrarComSaldo, locaisComEstoque, locaisComParada, maisRecentesPrimeiro, rotularEstoque, saldo } from "./operacoes";

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
