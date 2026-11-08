import type { DeliveryStatus } from "../api/types";
import { statusDe } from "../apresentacao/statusEntrega";

export function StatusBadge({ status }: { status: DeliveryStatus }) {
  const { rotulo, caixa, Icone, riscado } = statusDe(status);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${caixa}`}>
      <Icone size={16} aria-hidden="true" />
      <span className={riscado ? "line-through" : ""}>{rotulo}</span>
    </span>
  );
}
