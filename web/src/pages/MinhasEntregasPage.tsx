import { PackageCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { CatalogoApi, EntregasApi } from "../api/ApiClient";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";
import { EntregaAdapter, type Entrega } from "../domain/EntregaAdapter";
import { aguardandoRecebimento, maisRecentesPrimeiro } from "../domain/operacoes";

interface Props {
  api: CatalogoApi & EntregasApi;
  onRequest: () => void;
}

export function MinhasEntregasPage({ api, onRequest }: Props) {
  const [entregas, setEntregas] = useState<Entrega[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState<number | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [confirmada, setConfirmada] = useState(false);
  const [erroLista, setErroLista] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    const [deliveries, locations] = await Promise.all([api.deliveries(), api.locations()]);
    const adapter = new EntregaAdapter((id) => locations.find((l) => l.id === id)?.name ?? id);
    setEntregas(maisRecentesPrimeiro(deliveries).map((d) => adapter.adaptar(d)));
  }, [api]);

  useEffect(() => {
    carregar().catch((err: Error) => setError(err.message));
  }, [carregar]);

  async function confirmar(id: number) {
    setConfirmando(id);
    setErroAcao(null);
    setConfirmada(false);
    setErroLista(null);
    try {
      await api.confirmReceipt(id);
      setConfirmada(true);
      await carregar().catch(() =>
        setErroLista("Recebimento confirmado, mas a lista não atualizou. Recarregue a página para ver o novo status."),
      );
    } catch (err) {
      setErroAcao(err instanceof Error ? err.message : "Não foi possível confirmar o recebimento. Tente de novo.");
    } finally {
      setConfirmando(null);
    }
  }

  if (error) return <p role="alert" className="text-vermelho-600">{error}</p>;
  if (!entregas) return <p className="text-neutro-500">Carregando…</p>;

  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Minhas entregas</h1>
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
                  aguardandoRecebimento(e) ? (
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
