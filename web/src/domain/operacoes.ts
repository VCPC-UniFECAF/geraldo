// PROGRAMAÇÃO FUNCIONAL: funções puras com filter / map / sort, sem alterar a lista original.
import type { Delivery, DeliveryStatus, Location, Priority, StockEntry } from "../api/types";

export const saldo = (e: StockEntry): number => e.quantity - e.reserved;

export const filtrarComSaldo = (estoque: StockEntry[]): StockEntry[] => estoque.filter((e) => saldo(e) > 0);

export interface Opcao {
  valor: string;
  rotulo: string;
}

export const rotularEstoque = (estoque: StockEntry[]): Opcao[] =>
  estoque.map((e) => ({ valor: e.item_id, rotulo: `${e.item_name} (${saldo(e)} disponíveis)` }));

export const locaisComParada = (locais: Location[]): Location[] => locais.filter((l) => l.waypoint);

export const locaisComEstoque = (locais: Location[]): Location[] => locaisComParada(locais).filter((l) => l.has_stock);

export const maisRecentesPrimeiro = <T extends { created_at: string }>(itens: T[]): T[] =>
  [...itens].sort((a, b) => b.created_at.localeCompare(a.created_at));

export const aguardandoRecebimento = (e: { status: DeliveryStatus }): boolean => e.status === "AGUARDANDO_RECEBIMENTO";

export const abaixoDoMinimo = (estoque: StockEntry[]): StockEntry[] => estoque.filter((e) => e.quantity < e.minimum);

// Quem está abaixo do mínimo vem primeiro; a ordem original é mantida dentro de cada grupo.
export const abaixoDoMinimoPrimeiro = (estoque: StockEntry[]): StockEntry[] => [
  ...abaixoDoMinimo(estoque),
  ...estoque.filter((e) => e.quantity >= e.minimum),
];

const ORDEM_DA_PRIORIDADE: Record<Priority, number> = { critica: 0, media: 1, rotina: 2 };

export const emAndamento = (entregas: Delivery[]): Delivery[] =>
  entregas.filter((e) => e.status === "EM_ROTA" || e.status === "AGUARDANDO_RECEBIMENTO");

// Mesma ordem em que o robô pega o trabalho: prioridade crítica < média < rotina, depois FIFO por id.
export const filaDeEspera = (entregas: Delivery[]): Delivery[] =>
  entregas
    .filter((e) => e.status === "NA_FILA" || e.status === "PENDENTE_APROVACAO")
    .sort((a, b) => ORDEM_DA_PRIORIDADE[a.priority] - ORDEM_DA_PRIORIDADE[b.priority] || a.id - b.id);
