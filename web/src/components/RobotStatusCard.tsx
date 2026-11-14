import { Bot, TriangleAlert } from "lucide-react";
import type { Telemetry } from "../api/types";
import { duracao } from "../apresentacao/formato";
import { estadoRoboDe } from "../apresentacao/estadoRobo";
import { bateriaBaixa, segundosAteChegar } from "../domain/telemetria";
import { Card } from "./Card";

interface Props {
  telemetria: Telemetry | null;
  entrega: string | null;
}

export function RobotStatusCard({ telemetria, entrega }: Props) {
  return (
    <Card role="region" aria-label="Estado do robô" className="grid content-start gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bot size={24} aria-hidden="true" className="text-azul-600" />
          <h2 className="font-display text-lg font-semibold">G.E.R.A.L.D.O.</h2>
        </div>
        {telemetria && <EstadoBadge telemetria={telemetria} />}
      </div>
      {telemetria ? (
        <Detalhes telemetria={telemetria} entrega={entrega} />
      ) : (
        <p className="text-sm text-neutro-500">Sem sinal do robô. Confira se a simulação está ligada.</p>
      )}
    </Card>
  );
}

function EstadoBadge({ telemetria }: { telemetria: Telemetry }) {
  const { rotulo, caixa, Icone } = estadoRoboDe(telemetria.robot_state);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${caixa}`}>
      <Icone size={16} aria-hidden="true" />
      {rotulo}
    </span>
  );
}

function Detalhes({ telemetria, entrega }: { telemetria: Telemetry; entrega: string | null }) {
  const segundos = segundosAteChegar(telemetria.route);
  const baixa = bateriaBaixa(telemetria.battery);
  const bateria = Math.min(100, Math.max(0, Math.round(telemetria.battery)));
  return (
    <dl className="grid gap-3 text-sm">
      <div>
        <dt className="text-xs text-neutro-500">Entrega</dt>
        <dd>{entrega ?? "Sem entrega em curso"}</dd>
      </div>
      <div>
        <dt className="text-xs text-neutro-500">Chegada estimada</dt>
        <dd className="tabular-nums">{segundos === null ? "—" : `Cerca de ${duracao(segundos)}`}</dd>
      </div>
      <div>
        <dt className="text-xs text-neutro-500">Bateria</dt>
        <dd className="flex items-center gap-3">
          <div
            role="progressbar"
            aria-label="Bateria"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={bateria}
            className="h-2 flex-1 overflow-hidden rounded-full bg-neutro-100"
          >
            <div className={`h-full rounded-full ${baixa ? "bg-vermelho-500" : "bg-azul-500"}`} style={{ width: `${bateria}%` }} />
          </div>
          <span className="w-10 text-right font-semibold tabular-nums">{bateria}%</span>
        </dd>
        {baixa && (
          <p className="mt-1 flex items-center gap-1.5 text-xs font-semibold text-vermelho-600">
            <TriangleAlert size={16} aria-hidden="true" />
            Bateria baixa
          </p>
        )}
      </div>
    </dl>
  );
}
