import type { Telemetry } from "../api/types";
import { enquadrar } from "../domain/mapa";
import { Card } from "./Card";

const LARGURA = 320;
const ALTURA = 200;
const TAMANHO_DO_ROBO = 6;
const TAMANHO_DA_SETA = 14;

const metros = (valor: number) => valor.toFixed(1).replace(".", ",");
const graus = (radianos: number) => Math.round((radianos * 180) / Math.PI);

// Mapa simples (a visão 2D do hospital inteiro é do app instalável): robô, rota em azul e obstáculos em aviso.
export function TelemetryPanel({ telemetria }: { telemetria: Telemetry | null }) {
  return (
    <Card role="region" aria-label="Mapa e posição do robô" className="grid content-start gap-3">
      <h2 className="font-display text-lg font-semibold">Posição do robô</h2>
      {telemetria ? <Conteudo telemetria={telemetria} /> : <p className="text-sm text-neutro-500">Sem dados do robô ainda.</p>}
    </Card>
  );
}

function Conteudo({ telemetria }: { telemetria: Telemetry }) {
  const vista = enquadrar(telemetria, LARGURA, ALTURA);
  const total = vista.obstaculos.length;
  return (
    <>
      <svg
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        role="img"
        aria-label="Mapa simples com o robô, a rota e os obstáculos"
        className="w-full rounded-controle bg-fundo"
      >
        {vista.rota.length > 1 && (
          <polyline
            points={vista.rota.map((p) => `${p.x},${p.y}`).join(" ")}
            className="fill-none stroke-azul-500"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {vista.obstaculos.map((o, i) => (
          <circle key={i} data-obstaculo cx={o.x} cy={o.y} r={o.raio} className="fill-aviso-50 stroke-aviso-500" strokeWidth={1.5} />
        ))}
        <line
          x1={vista.robo.x}
          y1={vista.robo.y}
          x2={vista.robo.x + TAMANHO_DA_SETA * Math.cos(vista.robo.yaw)}
          y2={vista.robo.y - TAMANHO_DA_SETA * Math.sin(vista.robo.yaw)}
          className="stroke-azul-800"
          strokeWidth={3}
          strokeLinecap="round"
        />
        <circle cx={vista.robo.x} cy={vista.robo.y} r={TAMANHO_DO_ROBO} className="fill-azul-600 stroke-branco" strokeWidth={2} />
      </svg>
      <dl className="grid gap-2 text-sm md:grid-cols-3">
        <div>
          <dt className="text-xs text-neutro-500">Posição</dt>
          <dd className="tabular-nums">{`x ${metros(telemetria.pose.x)} m · y ${metros(telemetria.pose.y)} m`}</dd>
        </div>
        <div>
          <dt className="text-xs text-neutro-500">Direção</dt>
          <dd className="tabular-nums">{`${graus(telemetria.pose.yaw)}°`}</dd>
        </div>
        <div>
          <dt className="text-xs text-neutro-500">Obstáculos</dt>
          <dd className="tabular-nums">{total === 0 ? "Nenhum obstáculo" : `${total} ${total === 1 ? "obstáculo" : "obstáculos"}`}</dd>
        </div>
      </dl>
    </>
  );
}
