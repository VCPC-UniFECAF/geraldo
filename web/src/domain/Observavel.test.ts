import { Observavel, type Observador } from "./Observavel";

class Caixa extends Observavel<string> {
  avisar(msg: string) {
    this.notificar(msg);
  }
}

test("avisa todos os observers, na ordem em que foram adicionados", () => {
  const ordem: string[] = [];
  const caixa = new Caixa();
  caixa.adicionarObserver({ atualizar: (m) => ordem.push(`a:${m}`) });
  caixa.adicionarObserver({ atualizar: (m) => ordem.push(`b:${m}`) });
  caixa.avisar("oi");
  expect(ordem).toEqual(["a:oi", "b:oi"]);
});

test("observer removido não é mais avisado", () => {
  const recebidos: string[] = [];
  const observer: Observador<string> = { atualizar: (m) => recebidos.push(m) };
  const caixa = new Caixa();
  caixa.adicionarObserver(observer);
  caixa.avisar("1");
  caixa.removerObserver(observer);
  caixa.avisar("2");
  expect(recebidos).toEqual(["1"]);
});
