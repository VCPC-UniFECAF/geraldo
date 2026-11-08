import type { SessaoApi } from "../api/ApiClient";
import { Observavel, type Observador } from "./Observavel";

export interface EventoSessao {
  tipo: "entrou";
  token: string;
}

// Sujeito: quem entra no sistema avisa os observers (como Pedido.confirmar() no repositório).
export class Sessao extends Observavel<EventoSessao> {
  readonly #api: SessaoApi;

  constructor(api: SessaoApi) {
    super();
    this.#api = api;
  }

  async entrar(usuario: string, senha: string): Promise<void> {
    const { access_token } = await this.#api.login(usuario, senha);
    this.notificar({ tipo: "entrou", token: access_token });
  }
}

// Observer concreto: guarda o token no cliente da API para as próximas chamadas.
export class TokenObserver implements Observador<EventoSessao> {
  readonly #api: SessaoApi;

  constructor(api: SessaoApi) {
    this.#api = api;
  }

  atualizar(evento: EventoSessao): void {
    this.#api.definirToken(evento.token);
  }
}
