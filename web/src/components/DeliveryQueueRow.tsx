import type { ReactNode } from "react";
import { horario } from "../apresentacao/formato";
import type { Entrega } from "../domain/EntregaAdapter";
import { PriorityBadge } from "./PriorityBadge";
import { StatusBadge } from "./StatusBadge";

export function DeliveryQueueRow({ entrega, acao }: { entrega: Entrega; acao?: ReactNode }) {
  const itens = entrega.itens.map((i) => `${i.quantidade} × ${i.nome}`).join(", ");
  return (
    <li className="flex flex-col gap-2 rounded-controle bg-fundo px-3 py-3 md:flex-row md:items-center md:gap-3">
      <span className="w-12 text-xs tabular-nums text-neutro-500">{horario(entrega.solicitadaEm)}</span>
      <span className="min-w-0 flex-1 text-sm">
        {itens} · {entrega.origem} → {entrega.destino}
      </span>
      <span className="flex flex-wrap items-center gap-2">
        <PriorityBadge priority={entrega.prioridade} />
        <StatusBadge status={entrega.status} />
        {acao}
      </span>
    </li>
  );
}
