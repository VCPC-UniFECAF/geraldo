import type { DeliveryCreate, Priority } from "../api/types";

export class SolicitacaoInvalida extends Error {}

// BUILDER: monta o pedido passo a passo e só valida na hora do build().
export class SolicitacaoBuilder {
  #origem = "";
  #destino = "";
  #itemId = "";
  #quantidade = 0;
  #prioridade: Priority = "media";

  origem(id: string): this {
    this.#origem = id;
    return this;
  }

  destino(id: string): this {
    this.#destino = id;
    return this;
  }

  item(id: string, quantidade: number): this {
    this.#itemId = id;
    this.#quantidade = quantidade;
    return this;
  }

  prioridade(valor: Priority): this {
    this.#prioridade = valor;
    return this;
  }

  build(): DeliveryCreate {
    if (!Number.isInteger(this.#quantidade) || this.#quantidade < 1) {
      throw new SolicitacaoInvalida("Informe uma quantidade maior que zero.");
    }
    if (!this.#itemId) throw new SolicitacaoInvalida("Escolha um medicamento ou insumo.");
    if (this.#origem === this.#destino) throw new SolicitacaoInvalida("Origem e destino precisam ser diferentes.");
    return {
      origin_id: this.#origem,
      dest_id: this.#destino || null,
      items: [{ item_id: this.#itemId, quantity: this.#quantidade }],
      priority: this.#prioridade,
    };
  }
}
