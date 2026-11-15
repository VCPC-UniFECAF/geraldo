import { Check, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, type AprovacoesApi, type CatalogoApi, type EntregasApi } from "../api/ApiClient";
import type { Me } from "../api/types";
import { AlertBanner } from "../components/AlertBanner";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";
import { EntregaAdapter, type Entrega } from "../domain/EntregaAdapter";
import { MOTIVO_MAX, validarMotivo } from "../domain/motivo";
import { pendentesDeAprovacao, podeAprovar, podeAprovarPedido } from "../domain/operacoes";

interface Props {
  api: EntregasApi & AprovacoesApi & CatalogoApi;
  usuario: Me;
  intervaloMs?: number;
}

const CAMPO = "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 py-2 text-base";

// Pedidos críticos esperando a assinatura do farmacêutico. Recarrega sozinho: o pedido chega sem ninguém tocar na tela.
export function AprovacoesPanel({ api, usuario, intervaloMs = 5000 }: Props) {
  const [pedidos, setPedidos] = useState<Entrega[] | null>(null);
  const [sessaoExpirada, setSessaoExpirada] = useState(false);
  const [erroRecarga, setErroRecarga] = useState<string | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [recusando, setRecusando] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");
  const [erroMotivo, setErroMotivo] = useState<string | null>(null);
  const aprova = podeAprovar(usuario.role);

  const carregar = useCallback(async () => {
    const [entregas, locais] = await Promise.all([api.deliveries(), api.locations()]);
    const adapter = new EntregaAdapter((id) => locais.find((l) => l.id === id)?.name ?? id);
    setPedidos(pendentesDeAprovacao(entregas).map((d) => adapter.adaptar(d)));
    setErroRecarga(null);
  }, [api]);

  const falhou = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      setSessaoExpirada(true);
      setErroRecarga(null);
    } else setErroRecarga(err instanceof Error ? err.message : "Erro desconhecido. Tente de novo.");
  }, []);

  useEffect(() => {
    carregar().catch(falhou);
  }, [carregar, falhou]);

  useEffect(() => {
    if (sessaoExpirada) return;
    const id = setInterval(() => carregar().catch(falhou), intervaloMs);
    return () => clearInterval(id);
  }, [carregar, falhou, intervaloMs, sessaoExpirada]);

  async function agir(acao: () => Promise<unknown>, sucesso: string) {
    setOcupado(true);
    setErroAcao(null);
    setAviso(null);
    try {
      await acao();
      setAviso(sucesso);
      setRecusando(null);
      setMotivo("");
      await carregar().catch(falhou);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) falhou(err);
      else setErroAcao(err instanceof Error ? err.message : "Não foi possível concluir. Tente de novo.");
    } finally {
      setOcupado(false);
    }
  }

  function abrirRecusa(id: number) {
    setRecusando(id);
    setMotivo("");
    setErroMotivo(null);
    setErroAcao(null);
    setAviso(null);
  }

  function confirmarRecusa(e: FormEvent) {
    e.preventDefault();
    const erro = validarMotivo(motivo);
    setErroMotivo(erro);
    if (erro || recusando === null) return;
    const id = recusando;
    void agir(() => api.rejectDelivery(id, motivo.trim()), `Entrega ${id} recusada. O solicitante verá o motivo.`);
  }

  return (
    <section aria-labelledby="titulo-aprovacoes" className="grid gap-4">
      <h2 id="titulo-aprovacoes" className="font-display text-xl font-semibold">Aprovações</h2>
      {sessaoExpirada && <AlertBanner>Sua sessão expirou. Entre de novo para ver os pedidos pendentes.</AlertBanner>}
      {erroRecarga && <AlertBanner>Não foi possível atualizar os pedidos. {erroRecarga}</AlertBanner>}
      {erroAcao && <AlertBanner>{erroAcao}</AlertBanner>}
      {aviso && (
        <p role="status" className="rounded-controle bg-sucesso-50 px-4 py-3 text-sucesso-700">
          {aviso}
        </p>
      )}
      {!aprova && <p className="text-sm text-neutro-500">Só o farmacêutico aprova ou recusa pedidos críticos.</p>}
      <Card>
        {pedidos === null ? (
          <p className="text-neutro-500">Carregando…</p>
        ) : pedidos.length === 0 ? (
          <p className="py-4 text-center text-neutro-500">Nenhum pedido crítico esperando a sua assinatura.</p>
        ) : (
          <ul className="grid gap-2">
            {pedidos.map((p) => (
              <DeliveryQueueRow
                key={p.id}
                entrega={p}
                acao={
                  aprova ? (
                    <>
                      {podeAprovarPedido(usuario, p) ? (
                        <Button aria-label={`Aprovar entrega ${p.id}`} disabled={ocupado} onClick={() => void agir(() => api.approveDelivery(p.id), `Entrega ${p.id} aprovada. O robô vai buscar assim que estiver livre.`)}>
                          <Check size={20} aria-hidden="true" />
                          Aprovar
                        </Button>
                      ) : (
                        <span className="text-sm text-neutro-500">Outro farmacêutico precisa aprovar</span>
                      )}
                      <Button variant="secundario" aria-label={`Recusar entrega ${p.id}`} disabled={ocupado} onClick={() => abrirRecusa(p.id)}>
                        <X size={20} aria-hidden="true" />
                        Recusar
                      </Button>
                    </>
                  ) : undefined
                }
              />
            ))}
          </ul>
        )}
      </Card>
      {aprova && recusando !== null && (
        <Card>
          <form onSubmit={confirmarRecusa} className="grid gap-3" noValidate>
            <label htmlFor="motivo-recusa" className="text-sm font-medium">
              Motivo da recusa
            </label>
            <textarea id="motivo-recusa" className={CAMPO} rows={3} maxLength={MOTIVO_MAX + 20} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            <p className="text-xs text-neutro-500">Entrega {recusando}: o solicitante lê este texto em Minhas entregas.</p>
            {erroMotivo && (
              <p role="alert" className="text-sm text-vermelho-600">
                {erroMotivo}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={ocupado}>
                Confirmar recusa
              </Button>
              <Button variant="fantasma" disabled={ocupado} onClick={() => setRecusando(null)}>
                Cancelar
              </Button>
            </div>
          </form>
        </Card>
      )}
    </section>
  );
}
