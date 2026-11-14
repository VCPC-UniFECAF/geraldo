import type { StockEntry } from "../api/types";
import { nivelDe, preenchimento } from "../apresentacao/nivelEstoque";

export function StockLevelBar({ entrada, local }: { entrada: StockEntry; local: string }) {
  const nivel = nivelDe(entrada.quantity, entrada.minimum);
  const { Icone } = nivel;
  return (
    <li className="grid gap-2 rounded-controle bg-fundo px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">{entrada.item_name}</p>
          <p className="text-xs text-neutro-500">{local}</p>
        </div>
        <p className="font-display text-lg font-bold tabular-nums">{entrada.quantity}</p>
      </div>
      <div
        role="progressbar"
        aria-label={`Nível de ${entrada.item_name}`}
        aria-valuemin={0}
        aria-valuemax={Math.max(entrada.quantity, entrada.minimum * 2)}
        aria-valuenow={entrada.quantity}
        className="h-2 overflow-hidden rounded-full bg-neutro-100"
      >
        <div className={`h-full rounded-full ${nivel.barra}`} style={{ width: `${preenchimento(entrada.quantity, entrada.minimum)}%` }} />
      </div>
      <p className={`flex flex-wrap items-center gap-x-2 text-xs ${nivel.texto}`}>
        {Icone && <Icone size={16} aria-hidden="true" />}
        {nivel.rotulo && <span className="font-semibold">{nivel.rotulo}</span>}
        <span className="tabular-nums">
          Mínimo {entrada.minimum} · reservado {entrada.reserved}
        </span>
      </p>
    </li>
  );
}
