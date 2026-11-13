import { dataCurta, horario } from "./formato";

test("formata data e hora no fuso de São Paulo", () => {
  const data = new Date("2026-11-09T13:22:00Z");
  expect(dataCurta(data)).toBe("09/11");
  expect(horario(data)).toBe("10:22");
});
