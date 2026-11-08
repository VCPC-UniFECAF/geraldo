import type { DeliveryStatus, Delivery, Priority } from "../api/types";

// O que as telas usam: nomes legíveis e data de verdade, em vez do formato do backend.
export interface Entrega {
  id: number;
  origem: string;
  destino: string;
  itens: { nome: string; quantidade: number }[];
  prioridade: Priority;
  status: DeliveryStatus;
  solicitadaEm: Date;
}

const legivel = (id: string): string => {
  const texto = id.replace(/-/g, " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
};

// ADAPTER: traduz o contrato do backend (Delivery) para o modelo da interface (Entrega).
export class EntregaAdapter {
  readonly #nomeDoLocal: (id: string) => string;

  constructor(nomeDoLocal: (id: string) => string) {
    this.#nomeDoLocal = nomeDoLocal;
  }

  adaptar(entrega: Delivery): Entrega {
    return {
      id: entrega.id,
      origem: this.#nomeDoLocal(entrega.origin_id),
      destino: this.#nomeDoLocal(entrega.dest_id),
      itens: entrega.items.map((i) => ({ nome: legivel(i.item_id), quantidade: i.quantity })),
      prioridade: entrega.priority,
      status: entrega.status,
      solicitadaEm: new Date(entrega.created_at),
    };
  }
}
