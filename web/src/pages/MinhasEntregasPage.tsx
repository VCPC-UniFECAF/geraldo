import { PackageCheck } from "lucide-react";
import { useEffect, useState } from "react";
import type { CatalogoApi, EntregasApi } from "../api/ApiClient";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";
import { EntregaAdapter, type Entrega } from "../domain/EntregaAdapter";
import { maisRecentesPrimeiro } from "../domain/operacoes";

interface Props {
  api: CatalogoApi & EntregasApi;
  onRequest: () => void;
}

export function MinhasEntregasPage({ api, onRequest }: Props) {
  const [entregas, setEntregas] = useState<Entrega[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.deliveries(), api.locations()])
      .then(([deliveries, locations]) => {
        const adapter = new EntregaAdapter((id) => locations.find((l) => l.id === id)?.name ?? id);
        setEntregas(maisRecentesPrimeiro(deliveries).map((d) => adapter.adaptar(d)));
      })
      .catch((err: Error) => setError(err.message));
  }, [api]);

  if (error) return <p role="alert" className="text-vermelho-600">{error}</p>;
  if (!entregas) return <p className="text-neutro-500">Carregando…</p>;

  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Minhas entregas</h1>
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
              <DeliveryQueueRow key={e.id} entrega={e} />
            ))}
          </ul>
        )}
      </Card>
    </section>
  );
}
