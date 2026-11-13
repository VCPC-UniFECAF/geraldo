import { useState } from "react";
import type { CatalogoApi, HistoricoApi } from "../api/ApiClient";
import { Card } from "../components/Card";
import { Tabs } from "../components/Tabs";
import { HistoricoPanel } from "./estoque/HistoricoPanel";
import { SaldosPanel } from "./estoque/SaldosPanel";

const ABAS = [
  { id: "saldos", rotulo: "Saldos" },
  { id: "historico", rotulo: "Histórico" },
];

export function EstoquePage({ api }: { api: CatalogoApi & HistoricoApi }) {
  const [aba, setAba] = useState("saldos");
  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Estoque</h1>
      <Card className="mt-4 grid gap-4">
        <Tabs abas={ABAS} ativa={aba} onChange={setAba} rotulo="Seções do estoque" />
        {aba === "saldos" ? <SaldosPanel api={api} /> : <HistoricoPanel api={api} />}
      </Card>
    </section>
  );
}
