import type { Movement, MovementType } from "../api/types";

// O que as telas usam: nomes legíveis e data de verdade.
export interface Movimento {
  id: number;
  quando: Date;
  tipo: MovementType;
  item: string;
  quantidade: number;
  local: string;
  entregaId: number | null;
}

// ADAPTER: traduz o contrato do backend (Movement) para o modelo da interface (Movimento).
export class MovimentoAdapter {
  readonly #nomeDoLocal: (id: string) => string;
  readonly #nomeDoItem: (id: string) => string;

  constructor(nomeDoLocal: (id: string) => string, nomeDoItem: (id: string) => string) {
    this.#nomeDoLocal = nomeDoLocal;
    this.#nomeDoItem = nomeDoItem;
  }

  adaptar(movimento: Movement): Movimento {
    return {
      id: movimento.id,
      quando: new Date(movimento.created_at),
      tipo: movimento.type,
      item: this.#nomeDoItem(movimento.item_id),
      quantidade: movimento.quantity,
      local: this.#nomeDoLocal(movimento.location_id),
      entregaId: movimento.delivery_id ?? null,
    };
  }
}
