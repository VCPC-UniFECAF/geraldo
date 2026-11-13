import { dataCurta, horario } from "../apresentacao/formato";
import { tipoMovimentoDe } from "../apresentacao/tiposMovimento";
import type { Movimento } from "../domain/MovimentoAdapter";

export function MovementLogRow({ movimento }: { movimento: Movimento }) {
  const { rotulo, sinal, caixa, Icone } = tipoMovimentoDe(movimento.tipo);
  return (
    <li className="flex flex-col gap-1 rounded-controle bg-fundo px-3 py-3 md:flex-row md:items-center md:gap-3">
      <span className="w-24 text-xs tabular-nums text-neutro-500">
        {dataCurta(movimento.quando)} {horario(movimento.quando)}
      </span>
      <span className={`inline-flex w-fit items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${caixa}`}>
        <Icone size={16} aria-hidden="true" />
        {rotulo}
      </span>
      <span className="min-w-0 flex-1 text-sm">
        {movimento.item} · {movimento.local}
        {movimento.entregaId !== null && <span className="text-neutro-500"> · Entrega #{movimento.entregaId}</span>}
      </span>
      <span className="text-sm font-semibold tabular-nums">{`${sinal}${movimento.quantidade}`}</span>
    </li>
  );
}
