import { PRIORIDADES, prioridadeDe } from "./prioridades";
import { statusDe } from "./statusEntrega";

test("só a prioridade crítica tem aviso", () => {
  expect(prioridadeDe("critica").aviso).toBe("Prioridade crítica exige a assinatura do farmacêutico.");
  expect(prioridadeDe("media").aviso).toBeNull();
  expect(prioridadeDe("rotina").aviso).toBeNull();
});

test("as prioridades aparecem na ordem crítica, média, rotina", () => {
  expect(PRIORIDADES.map((p) => p.valor)).toEqual(["critica", "media", "rotina"]);
});

test("só o status cancelada aparece riscado", () => {
  expect(statusDe("CANCELADA").riscado).toBe(true);
  expect(statusDe("ENTREGUE").riscado).toBe(false);
});
