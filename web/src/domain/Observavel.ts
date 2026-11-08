// OBSERVER: o sujeito mantém a lista e avisa todo mundo quando algo acontece.
export interface Observador<T> {
  atualizar(evento: T): void;
}

export class Observavel<T> {
  readonly #observadores: Observador<T>[] = [];

  adicionarObserver(observador: Observador<T>): void {
    this.#observadores.push(observador);
  }

  removerObserver(observador: Observador<T>): void {
    const i = this.#observadores.indexOf(observador);
    if (i >= 0) this.#observadores.splice(i, 1);
  }

  protected notificar(evento: T): void {
    for (const observador of [...this.#observadores]) observador.atualizar(evento);
  }
}
