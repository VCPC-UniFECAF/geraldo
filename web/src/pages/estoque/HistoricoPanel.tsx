import { useEffect, useState } from "react";
import type { CatalogoApi, HistoricoApi } from "../../api/ApiClient";
import { MovementLogRow } from "../../components/MovementLogRow";
import { legivel } from "../../domain/EntregaAdapter";
import { MovimentoAdapter, type Movimento } from "../../domain/MovimentoAdapter";
import { maisRecentesPrimeiro } from "../../domain/operacoes";

export function HistoricoPanel({ api }: { api: CatalogoApi & HistoricoApi }) {
  const [movimentos, setMovimentos] = useState<Movimento[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.movements(), api.locations(), api.stock()])
      .then(([lista, locais, estoque]) => {
        const adapter = new MovimentoAdapter(
          (id) => locais.find((l) => l.id === id)?.name ?? id,
          (id) => estoque.find((e) => e.item_id === id)?.item_name ?? legivel(id),
        );
        setMovimentos(maisRecentesPrimeiro(lista).map((m) => adapter.adaptar(m)));
      })
      .catch((err: Error) => setErro(err.message));
  }, [api]);

  if (erro) return <p role="alert" className="text-vermelho-600">{erro}</p>;
  if (!movimentos) return <p className="text-neutro-500">Carregando…</p>;
  if (movimentos.length === 0) return <p className="text-sm text-neutro-500">Nenhuma movimentação ainda.</p>;
  return (
    <ul className="grid gap-2">
      {movimentos.map((m) => (
        <MovementLogRow key={m.id} movimento={m} />
      ))}
    </ul>
  );
}
