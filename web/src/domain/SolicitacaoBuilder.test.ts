import { SolicitacaoBuilder, SolicitacaoInvalida } from "./SolicitacaoBuilder";

const valido = () => new SolicitacaoBuilder().origem("farmacia").destino("consultorio1").item("dipirona-500mg", 5);

test("monta o pedido no formato do contrato, com prioridade média por padrão", () => {
  expect(valido().build()).toEqual({
    origin_id: "farmacia",
    dest_id: "consultorio1",
    items: [{ item_id: "dipirona-500mg", quantity: 5 }],
    priority: "media",
  });
});

test("aceita outra prioridade", () => {
  expect(valido().prioridade("critica").build().priority).toBe("critica");
});

test("destino vazio vira null (a API usa o local do usuário)", () => {
  expect(new SolicitacaoBuilder().origem("farmacia").item("dipirona-500mg", 1).build().dest_id).toBeNull();
});

test.each([0, -1, 1.5, Number.NaN])("quantidade %s é recusada", (quantidade) => {
  expect(() => valido().item("dipirona-500mg", quantidade).build()).toThrow("Informe uma quantidade maior que zero.");
});

test("sem item é recusado", () => {
  expect(() => valido().item("", 1).build()).toThrow("Escolha um medicamento ou insumo.");
});

test("origem igual ao destino é recusada", () => {
  expect(() => valido().destino("farmacia").build()).toThrow(SolicitacaoInvalida);
  expect(() => valido().destino("farmacia").build()).toThrow("Origem e destino precisam ser diferentes.");
});
