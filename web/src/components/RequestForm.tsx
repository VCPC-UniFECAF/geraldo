import { useEffect, useState, type FormEvent } from "react";
import type { DeliveryCreate, Location, Priority, StockEntry } from "../api/types";
import { PRIORIDADES, prioridadeDe } from "../apresentacao/prioridades";
import { filtrarComSaldo, locaisComEstoque, locaisComParada, rotularEstoque, type Opcao } from "../domain/operacoes";
import { SolicitacaoBuilder, SolicitacaoInvalida } from "../domain/SolicitacaoBuilder";
import { Button } from "./Button";

const FIELD =
  "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 text-base text-tinta " +
  "focus:border-azul-500 focus:outline-none focus:ring-2 focus:ring-azul-200";
const LABEL = "mb-1 block text-sm font-medium text-neutro-700";

interface Props {
  locations: Location[];
  defaultDestId: string | null;
  loadStock: (originId: string) => Promise<StockEntry[]>;
  onSubmit: (body: DeliveryCreate) => Promise<void>;
}

export function RequestForm({ locations, defaultDestId, loadStock, onSubmit }: Props) {
  const places = locaisComParada(locations);
  const origins = locaisComEstoque(locations);
  const [originId, setOriginId] = useState(origins.find((l) => l.id === "farmacia")?.id ?? origins[0]?.id ?? "");
  const [destId, setDestId] = useState(defaultDestId ?? "");
  const [opcoes, setOpcoes] = useState<Opcao[]>([]);
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [priority, setPriority] = useState<Priority>("media");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadStock(originId).then((entries) => {
      if (cancelled) return;
      const lista = rotularEstoque(filtrarComSaldo(entries));
      setOpcoes(lista);
      setItemId(lista[0]?.valor ?? "");
    });
    return () => {
      cancelled = true;
    };
  }, [originId, loadStock]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    let pedido: DeliveryCreate;
    try {
      pedido = new SolicitacaoBuilder().origem(originId).destino(destId).item(itemId, Number(quantity)).prioridade(priority).build();
    } catch (err) {
      if (err instanceof SolicitacaoInvalida) return setError(err.message);
      throw err;
    }
    setError(null);
    setBusy(true);
    try {
      await onSubmit(pedido);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível solicitar. Tente de novo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
      <div>
        <label htmlFor="origin" className={LABEL}>
          Origem
        </label>
        <select id="origin" className={FIELD} value={originId} onChange={(e) => setOriginId(e.target.value)}>
          {origins.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="item" className={LABEL}>
          Medicamento ou insumo
        </label>
        <select id="item" className={FIELD} value={itemId} onChange={(e) => setItemId(e.target.value)}>
          {opcoes.map((o) => (
            <option key={o.valor} value={o.valor}>
              {o.rotulo}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="quantity" className={LABEL}>
          Quantidade
        </label>
        <input
          id="quantity"
          type="number"
          inputMode="numeric"
          min={1}
          className={`${FIELD} tabular-nums`}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
      </div>

      <fieldset className="grid gap-2">
        <legend className={LABEL}>Prioridade</legend>
        <div className="grid grid-cols-3 gap-2">
          {PRIORIDADES.map((p) => (
            <label
              key={p.valor}
              className="flex min-h-controle cursor-pointer items-center justify-center gap-2 rounded-controle border border-neutro-200 bg-branco px-3 text-sm font-medium has-[:checked]:border-azul-500 has-[:checked]:bg-azul-50"
            >
              <input
                type="radio"
                name="priority"
                value={p.valor}
                checked={priority === p.valor}
                onChange={() => setPriority(p.valor)}
                className="accent-azul-500"
              />
              {p.rotulo}
            </label>
          ))}
        </div>
        {prioridadeDe(priority).aviso && <p className="text-sm text-vermelho-600">{prioridadeDe(priority).aviso}</p>}
      </fieldset>

      <div>
        <label htmlFor="dest" className={LABEL}>
          Destino
        </label>
        <select id="dest" className={FIELD} value={destId} onChange={(e) => setDestId(e.target.value)}>
          {places.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {error}
        </p>
      )}

      <Button type="submit" size="lg" disabled={busy || !itemId}>
        Solicitar medicamento
      </Button>
    </form>
  );
}
