import { useCallback, useEffect, useState } from "react";
import type { CatalogoApi, EntregasApi, RoboApi } from "../api/ApiClient";
import type { Delivery, Location } from "../api/types";
import { estadoRoboDe } from "../apresentacao/estadoRobo";
import { AlertBanner } from "../components/AlertBanner";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";
import { RobotStatusCard } from "../components/RobotStatusCard";
import { TelemetryPanel } from "../components/TelemetryPanel";
import { EntregaAdapter, type Entrega } from "../domain/EntregaAdapter";
import { emAndamento, filaDeEspera } from "../domain/operacoes";
import { bateriaBaixa } from "../domain/telemetria";
import type { TelemetriaCliente } from "../domain/TelemetriaCliente";
import { useTelemetria } from "../hooks/useTelemetria";

interface Props {
  api: CatalogoApi & EntregasApi & RoboApi;
  telemetria: TelemetriaCliente;
}

function Secao({ titulo, entregas, vazio }: { titulo: string; entregas: Entrega[]; vazio: string }) {
  return (
    <Card role="region" aria-label={titulo}>
      <h2 className="font-display text-lg font-semibold">{titulo}</h2>
      {entregas.length === 0 ? (
        <p className="mt-3 text-sm text-neutro-500">{vazio}</p>
      ) : (
        <ul className="mt-3 grid gap-2">
          {entregas.map((e) => (
            <DeliveryQueueRow key={e.id} entrega={e} />
          ))}
        </ul>
      )}
    </Card>
  );
}

export function PainelPage({ api, telemetria: cliente }: Props) {
  const snapshot = useCallback(() => api.telemetry(), [api]);
  const { telemetria, conexao } = useTelemetria(cliente, snapshot);
  const [dados, setDados] = useState<{ entregas: Delivery[]; locais: Location[] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const estado = telemetria?.robot_state;
  const entregaId = telemetria?.delivery_id ?? null;

  // Recarrega a fila quando o robô muda de estado ou de entrega (é o que muda a fila de verdade).
  useEffect(() => {
    let ativo = true;
    Promise.all([api.deliveries(), api.locations()])
      .then(([entregas, locais]) => {
        if (ativo) setDados({ entregas, locais });
      })
      .catch((err: Error) => {
        if (ativo) setErro(err.message);
      });
    return () => {
      ativo = false;
    };
  }, [api, estado, entregaId]);

  const nomeDoLocal = (id: string) => dados?.locais.find((l) => l.id === id)?.name ?? id;
  const adapter = new EntregaAdapter(nomeDoLocal);
  const adaptar = (lista: Delivery[]) => lista.map((d) => adapter.adaptar(d));
  const emCurso = dados?.entregas.find((e) => e.id === entregaId);
  const entrega = emCurso ? `Entrega #${emCurso.id} · ${nomeDoLocal(emCurso.dest_id)}` : entregaId !== null ? `Entrega #${entregaId}` : null;
  const emergenciaAtiva = telemetria ? estadoRoboDe(telemetria.robot_state).emEmergencia : false;

  return (
    <section className="grid gap-4">
      <h1 className="font-display text-2xl font-bold">Painel do robô</h1>
      {emergenciaAtiva && <AlertBanner>Parada de emergência ativa. O robô está parado até a liberação.</AlertBanner>}
      {telemetria && bateriaBaixa(telemetria.battery) && <AlertBanner>Bateria abaixo de 20%. Evite novos pedidos até a recarga.</AlertBanner>}
      {conexao === "reconectando" && <AlertBanner variante="info">Sem conexão com o robô. Tentando reconectar…</AlertBanner>}
      {erro && (
        <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {erro}
        </p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <RobotStatusCard telemetria={telemetria} entrega={entrega} />
        <TelemetryPanel telemetria={telemetria} />
      </div>
      <Secao titulo="Em andamento" entregas={dados ? adaptar(emAndamento(dados.entregas)) : []} vazio="Nenhuma entrega em andamento." />
      <Secao titulo="Fila de espera" entregas={dados ? adaptar(filaDeEspera(dados.entregas)) : []} vazio="Ninguém na fila." />
    </section>
  );
}
