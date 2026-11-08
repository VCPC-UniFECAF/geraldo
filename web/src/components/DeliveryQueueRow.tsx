import type { Entrega } from "../domain/EntregaAdapter";
import { PriorityBadge } from "./PriorityBadge";
import { StatusBadge } from "./StatusBadge";

const horario = (data: Date) =>
  data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });

export function DeliveryQueueRow({ entrega }: { entrega: Entrega }) {
  const itens = entrega.itens.map((i) => `${i.quantidade} × ${i.nome}`).join(", ");
  return (
    <li className="flex flex-col gap-2 rounded-controle bg-fundo px-3 py-3 md:flex-row md:items-center md:gap-3">
      <span className="w-12 text-xs tabular-nums text-neutro-500">{horario(entrega.solicitadaEm)}</span>
      <span className="flex-1 text-sm">
        {itens} · {entrega.origem} → {entrega.destino}
      </span>
      <span className="flex flex-wrap gap-2">
        <PriorityBadge priority={entrega.prioridade} />
        <StatusBadge status={entrega.status} />
      </span>
    </li>
  );
}
