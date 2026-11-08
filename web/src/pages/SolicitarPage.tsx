import { useCallback, useEffect, useState } from "react";
import type { CatalogoApi, EntregasApi, SessaoApi } from "../api/ApiClient";
import type { DeliveryCreate, Location, Me } from "../api/types";
import { Card } from "../components/Card";
import { RequestForm } from "../components/RequestForm";

interface Props {
  api: SessaoApi & CatalogoApi & EntregasApi;
}

export function SolicitarPage({ api }: Props) {
  const [data, setData] = useState<{ me: Me; locations: Location[] } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const loadStock = useCallback((originId: string) => api.stock(originId), [api]);

  useEffect(() => {
    Promise.all([api.me(), api.locations()])
      .then(([me, locations]) => setData({ me, locations }))
      .catch((err: Error) => setLoadError(err.message));
  }, [api]);

  async function submit(body: DeliveryCreate) {
    await api.createDelivery(body);
    setDone(true);
  }

  if (loadError) return <p role="alert" className="text-vermelho-600">{loadError}</p>;
  if (!data) return <p className="text-neutro-500">Carregando…</p>;

  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Solicitar medicamento</h1>
      <Card className="mt-4">
        <RequestForm locations={data.locations} defaultDestId={data.me.local_id} loadStock={loadStock} onSubmit={submit} />
      </Card>
      {done && (
        <p role="status" className="mt-4 rounded-controle bg-sucesso-50 px-4 py-3 text-sucesso-700">
          Entrega solicitada. Acompanhe em Minhas entregas.
        </p>
      )}
    </section>
  );
}
