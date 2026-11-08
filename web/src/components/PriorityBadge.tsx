import type { Priority } from "../api/types";
import { prioridadeDe } from "../apresentacao/prioridades";

export function PriorityBadge({ priority }: { priority: Priority }) {
  const p = prioridadeDe(priority);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${p.caixa}`}>
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${p.ponto}`} />
      {p.rotulo}
    </span>
  );
}
