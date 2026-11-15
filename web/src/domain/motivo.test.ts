import { validarMotivo } from "./motivo";

test("motivo de 3 a 200 caracteres (sem contar os espaços das pontas) é aceito", () => {
  expect(validarMotivo("abc")).toBeNull();
  expect(validarMotivo("  Sem justificativa  ")).toBeNull();
  expect(validarMotivo("x".repeat(200))).toBeNull();
});

test("motivo curto ou longo demais diz o que fazer", () => {
  const msg = "Escreva o motivo da recusa com 3 a 200 caracteres.";
  expect(validarMotivo("")).toBe(msg);
  expect(validarMotivo("   ab  ")).toBe(msg);
  expect(validarMotivo("x".repeat(201))).toBe(msg);
});
