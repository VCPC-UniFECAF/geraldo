import { PackageCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type CatalogoApi, type EntregasApi } from "../api/ApiClient";
import type { Me } from "../api/types";
import { AlertBanner } from "../components/AlertBanner";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";
import { EntregaAdapter, type Entrega } from "../domain/EntregaAdapter";
import { aguardandoRecebimento, maisRecentesPrimeiro } from "../domain/operacoes";

interface Props {
  api: CatalogoApi & EntregasApi;
  usuario: Pick<Me, "id" | "role">;
  onRequest: () => void;
  intervaloMs?: number;
}

export function MinhasEntregasPage({ api, usuario, onRequest, intervaloMs = 5000 }: Props) {
  const [entregas, setEntregas] = useState<Entrega[] | null>(null);
  const [sessaoExpirada, setSessaoExpirada] = useState(false);
  const [erroRecarga, setErroRecarga] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState<number | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [confirmada, setConfirmada] = useState(false);
  const [erroLista, setErroLista] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    const [deliveries, locations] = await Promise.all([api.deliveries(), api.locations()]);
    const adapter = new EntregaAdapter((id) => locations.find((l) => l.id === id)?.name ?? id);
    setEntregas(maisRecentesPrimeiro(deliveries).map((d) => adapter.adaptar(d)));
    setErroRecarga(null);
  }, [api]);

  // 401 = sessão expirada (como no Painel); qualquer outro erro aparece sem apagar a lista, e a próxima rodada tenta de novo.
  const falhou = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) setSessaoExpirada(true);
    else setErroRecarga(err instanceof Error ? err.message : "Erro desconhecido. Tente de novo.");
  }, []);

  useEffect(() => {
    carregar().catch(falhou);
  }, [carregar, falhou]);

  // O robô chega sem ninguém tocar na tela: recarrega sozinho; com a sessão expirada não adianta insistir.
  useEffect(() => {
    if (sessaoExpirada) return;
    const id = setInterval(() => carregar().catch(falhou), intervaloMs);
    return () => clearInterval(id);
  }, [carregar, falhou, intervaloMs, sessaoExpirada]);

  async function confirmar(id: number) {
    setConfirmando(id);
    setErroAcao(null);
    setConfirmada(false);
    setErroLista(null);
    try {
      await api.confirmReceipt(id);
      setConfirmada(true);
      await carregar().catch((err: unknown) =>
        err instanceof ApiError && err.status === 401
          ? falhou(err)
          : setErroLista("Recebimento confirmado, mas a lista não atualizou. Recarregue a página para ver o novo status."),
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) falhou(err);
      else setErroAcao(err instanceof Error ? err.message : "Não foi possível confirmar o recebimento. Tente de novo.");
    } finally {
      setConfirmando(null);
    }
  }

  const avisos = (
    <>
      {sessaoExpirada && (
        <div className="mt-4">
          <AlertBanner>Sua sessão expirou. Entre de novo para ver suas entregas.</AlertBanner>
        </div>
      )}
      {erroRecarga && (
        <p role="alert" className="mt-4 rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          Não foi possível atualizar a lista. {erroRecarga}
        </p>
      )}
    </>
  );
  if (!entregas) {
    if (sessaoExpirada || erroRecarga) return <section>{avisos}</section>;
    return <p className="text-neutro-500">Carregando…</p>;
  }

  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Minhas entregas</h1>
      {avisos}
      {confirmada && (
        <p role="status" className="mt-4 rounded-controle bg-sucesso-50 px-4 py-3 text-sucesso-700">
          Recebimento confirmado. A tampa do robô foi liberada.
        </p>
      )}
      {erroLista && (
        <p role="alert" className="mt-4 rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {erroLista}
        </p>
      )}
      {erroAcao && (
        <p role="alert" className="mt-4 rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {erroAcao}
        </p>
      )}
      <Card className="mt-4">
        {entregas.length === 0 ? (
          <div className="grid justify-items-center gap-3 py-6 text-center">
            <PackageCheck size={40} aria-hidden="true" className="text-neutro-300" />
            <p className="font-display text-lg font-semibold">Nenhuma entrega ainda</p>
            <p className="text-sm text-neutro-500">Solicite um medicamento para acompanhar a entrega aqui.</p>
            <Button onClick={onRequest}>Solicitar medicamento</Button>
          </div>
        ) : (
          <ul className="grid gap-2">
            {entregas.map((e) => (
              <DeliveryQueueRow
                key={e.id}
                entrega={e}
                acao={
                  aguardandoRecebimento(e) && (e.solicitanteId === usuario.id || usuario.role === "admin") ? (
                    <Button
                      variant="secundario"
                      className="w-full md:w-auto"
                      disabled={confirmando !== null}
                      aria-label={`Confirmar recebimento da entrega ${e.id}`}
                      onClick={() => confirmar(e.id)}
                    >
                      <PackageCheck size={20} aria-hidden="true" />
                      Confirmar recebimento
                    </Button>
                  ) : undefined
                }
              />
            ))}
          </ul>
        )}
      </Card>
    </section>
  );
}
