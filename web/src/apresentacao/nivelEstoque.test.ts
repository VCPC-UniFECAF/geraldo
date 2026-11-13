import { nivelDe, preenchimento } from "./nivelEstoque";

test.each([
  [6, 10, "abaixo"],
  [10, 10, "atencao"],
  [12, 10, "atencao"],
  [13, 10, "ok"],
  [420, 100, "ok"],
])("quantidade %s com mínimo %s é nível %s", (quantidade, minimo, esperado) => {
  expect(nivelDe(quantidade, minimo).valor).toBe(esperado);
});

test("só o nível abaixo do mínimo tem o texto Abaixo do mínimo e é vermelho", () => {
  expect(nivelDe(6, 10).rotulo).toBe("Abaixo do mínimo");
  expect(nivelDe(6, 10).barra).toBe("bg-vermelho-500");
  expect(nivelDe(13, 10).rotulo).toBeNull();
  expect(nivelDe(13, 10).barra).toBe("bg-azul-500");
  expect(nivelDe(11, 10).barra).toBe("bg-aviso-500");
});

test("a barra enche até o dobro do mínimo", () => {
  expect(preenchimento(0, 10)).toBe(0);
  expect(preenchimento(6, 10)).toBe(30);
  expect(preenchimento(10, 10)).toBe(50);
  expect(preenchimento(420, 100)).toBe(100);
  expect(preenchimento(5, 0)).toBe(100);
});
