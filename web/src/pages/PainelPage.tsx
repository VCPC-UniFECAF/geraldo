import { useCallback, useEffect, useState } from "react";
import type { CatalogoApi, EntregasApi, RoboApi } from "../api/ApiClient";
import type { Delivery, Location, Role } from "../api/types";
import { AlertBanner } from "../components/AlertBanner";
import { BotaoEmergencia } from "../components/BotaoEmergencia";
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
  role: Role;
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

export function PainelPage({ api, telemetria: cliente, role }: Props) {
  const snapshot = useCallback(() => api.telemetry(), [api]);
  const { telemetria, conexao } = useTelemetria(cliente, snapshot);
  const [dados, setDados] = useState<{ entregas: Delivery[]; locais: Location[] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  // `solicitado` é o que este painel acabou de pedir; null = sem pedido pendente, vale o que a telemetria diz.
  const [solicitado, setSolicitado] = useState<boolean | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erroEstop, setErroEstop] = useState<string | null>(null);

  const estado = telemetria?.robot_state;
  const entregaId = telemetria?.delivery_id ?? null;
  const robotParado = estado === "PARADA_EMERGENCIA";
  // A telemetria manda: só um pedido de ACIONAR ainda não confirmado liga o alerta sozinho; desligar nunca esconde a parada contra a telemetria.
  const emergenciaAtiva = robotParado || solicitado === true;

  // Recarrega a fila quando o robô muda de estado ou de entrega (é o que muda a fila de verdade).
  useEffect(() => {
    let ativo = true;
    Promise.all([api.deliveries(), api.locations()])
      .then(([entregas, locais]) => {
        if (ativo) {
          setDados({ entregas, locais });
          setErro(null);
        }
      })
      .catch((err: Error) => {
        if (ativo) setErro(err.message);
      });
    return () => {
      ativo = false;
    };
  }, [api, estado, entregaId]);

  // Quando a telemetria confirma o que pedimos, o pedido local deixa de ser necessário.
  useEffect(() => {
    if (solicitado !== null && telemetria && robotParado === solicitado) setSolicitado(null);
  }, [solicitado, telemetria, robotParado]);

  async function alternarEmergencia(ativar: boolean) {
    setOcupado(true);
    setErroEstop(null);
    try {
      await api.setEstop(ativar);
      setSolicitado(ativar ? true : null);
    } catch (err) {
      setErroEstop(err instanceof Error ? err.message : "Não foi possível acionar a parada de emergência. Tente de novo.");
    } finally {
      setOcupado(false);
    }
  }

  const nomeDoLocal = (id: string) => dados?.locais.find((l) => l.id === id)?.name ?? id;
  const adapter = new EntregaAdapter(nomeDoLocal);
  const adaptar = (lista: Delivery[]) => lista.map((d) => adapter.adaptar(d));
  const emCurso = dados?.entregas.find((e) => e.id === entregaId);
  const entrega = emCurso ? `Entrega #${emCurso.id} · ${nomeDoLocal(emCurso.dest_id)}` : entregaId !== null ? `Entrega #${entregaId}` : null;

  return (
    <section className="grid gap-4">
      <h1 className="font-display text-2xl font-bold">Painel do robô</h1>
      {emergenciaAtiva && <AlertBanner>Parada de emergência ativa. O robô está parado até a liberação.</AlertBanner>}
      {telemetria && bateriaBaixa(telemetria.battery) && <AlertBanner>Bateria abaixo de 20%. Evite novos pedidos até a recarga.</AlertBanner>}
      {conexao === "sessao_expirada" && <AlertBanner>Sua sessão expirou. Entre de novo para ver o robô ao vivo.</AlertBanner>}
      {conexao === "desistiu" && <AlertBanner>Não foi possível reconectar ao robô. Recarregue a página.</AlertBanner>}
      {conexao === "reconectando" && <AlertBanner variante="info">Sem conexão com o robô. Tentando reconectar…</AlertBanner>}
      {erro && (
        <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {erro}
        </p>
      )}
      <BotaoEmergencia role={role} ativo={emergenciaAtiva} ocupado={ocupado} onAlternar={alternarEmergencia} />
      {erroEstop && (
        <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {erroEstop}
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
