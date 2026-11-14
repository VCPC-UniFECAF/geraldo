import { useEffect, useState } from "react";
import type { CatalogoApi } from "../../api/ApiClient";
import type { Location, StockEntry } from "../../api/types";
import { AlertBanner } from "../../components/AlertBanner";
import { StockLevelBar } from "../../components/StockLevelBar";
import { abaixoDoMinimo, abaixoDoMinimoPrimeiro, locaisComEstoque } from "../../domain/operacoes";

const FIELD =
  "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 text-base text-tinta " +
  "focus:border-azul-500 focus:outline-none focus:ring-2 focus:ring-azul-200";

export function SaldosPanel({ api }: { api: CatalogoApi }) {
  const [locais, setLocais] = useState<Location[]>([]);
  const [localId, setLocalId] = useState("");
  const [estoque, setEstoque] = useState<StockEntry[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.locations().then(setLocais).catch((err: Error) => setErro(err.message));
  }, [api]);

  useEffect(() => {
    let cancelado = false;
    setEstoque(null);
    setErro(null);
    api
      .stock(localId || undefined)
      .then((entradas) => {
        if (!cancelado) setEstoque(entradas);
      })
      .catch((err: Error) => {
        if (!cancelado) setErro(err.message);
      });
    return () => {
      cancelado = true;
    };
  }, [api, localId]);

  const nomeDoLocal = (id: string) => locais.find((l) => l.id === id)?.name ?? id;
  const faltando = estoque ? abaixoDoMinimo(estoque).length : 0;

  return (
    <div className="grid gap-4">
      <div className="md:max-w-xs">
        <label htmlFor="local" className="mb-1 block text-sm font-medium text-neutro-700">
          Local
        </label>
        <select id="local" className={FIELD} value={localId} onChange={(e) => setLocalId(e.target.value)}>
          <option value="">Todos os locais</option>
          {locaisComEstoque(locais).map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>
      {erro && (
        <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {erro}
        </p>
      )}
      {faltando > 0 && (
        <AlertBanner>
          {faltando} {faltando === 1 ? "item abaixo do mínimo" : "itens abaixo do mínimo"}. Peça a reposição à farmácia.
        </AlertBanner>
      )}
      {estoque === null ? (
        !erro && <p className="text-neutro-500">Carregando…</p>
      ) : estoque.length === 0 ? (
        <p className="text-sm text-neutro-500">Nenhum item neste local.</p>
      ) : (
        <ul className="grid gap-2 md:grid-cols-2">
          {abaixoDoMinimoPrimeiro(estoque).map((e) => (
            <StockLevelBar key={`${e.location_id}/${e.item_id}`} entrada={e} local={nomeDoLocal(e.location_id)} />
          ))}
        </ul>
      )}
    </div>
  );
}
