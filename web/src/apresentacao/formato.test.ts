import { dataCurta, duracao, horario } from "./formato";

test("duracao mostra segundos até 59 s e depois minutos arredondados para cima", () => {
  expect(duracao(5)).toBe("5 s");
  expect(duracao(59)).toBe("59 s");
  expect(duracao(60)).toBe("1 min");
  expect(duracao(125)).toBe("3 min");
});

test("formata data e hora no fuso de São Paulo", () => {
  const data = new Date("2026-11-09T13:22:00Z");
  expect(dataCurta(data)).toBe("09/11");
  expect(horario(data)).toBe("10:22");
});
