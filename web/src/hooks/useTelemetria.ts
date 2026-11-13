import { useEffect, useState } from "react";
import type { Telemetry } from "../api/types";
import type { Observador } from "../domain/Observavel";
import type { EstadoConexao, EventoTelemetria, TelemetriaCliente } from "../domain/TelemetriaCliente";

// OBSERVER: liga o TelemetriaCliente ao React; o hook é o observador e cancela a assinatura no unmount. `snapshot` busca o primeiro estado (GET /telemetry) enquanto o
// WebSocket conecta; se o WebSocket responder antes, o dado dele vale mais. `snapshot` deve ser estável (useCallback).
export function useTelemetria(cliente: TelemetriaCliente, snapshot: () => Promise<Telemetry>) {
  const [telemetria, setTelemetria] = useState<Telemetry | null>(null);
  const [conexao, setConexao] = useState<EstadoConexao>("parado");

  useEffect(() => {
    let ativo = true;
    const observer: Observador<EventoTelemetria> = {
      atualizar: (evento) => {
        if (evento.tipo === "telemetria") setTelemetria(evento.dados);
        else setConexao(evento.estado);
      },
    };
    cliente.adicionarObserver(observer);
    snapshot()
      .then((inicial) => {
        if (ativo) setTelemetria((atual) => atual ?? inicial);
      })
      .catch(() => {}); // sem snapshot, o painel espera o WebSocket
    cliente.iniciar();
    return () => {
      ativo = false;
      cliente.removerObserver(observer);
      cliente.parar();
    };
  }, [cliente, snapshot]);

  return { telemetria, conexao };
}
