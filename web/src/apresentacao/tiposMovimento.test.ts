import { tipoMovimentoDe } from "./tiposMovimento";

test.each([
  ["RESERVA", "Reserva", "-"],
  ["BAIXA", "Baixa", "-"],
  ["CREDITO", "Crédito", "+"],
  ["ESTORNO", "Estorno", "+"],
] as const)("%s mostra %s com sinal %s", (valor, rotulo, sinal) => {
  expect(tipoMovimentoDe(valor).rotulo).toBe(rotulo);
  expect(tipoMovimentoDe(valor).sinal).toBe(sinal);
});

test("nenhum tipo de movimento usa vermelho", () => {
  for (const valor of ["RESERVA", "BAIXA", "CREDITO", "ESTORNO"] as const) {
    expect(tipoMovimentoDe(valor).caixa).not.toContain("vermelho");
  }
});
