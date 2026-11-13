import type { CatalogoApi } from "../api/ApiClient";
import { Card } from "../components/Card";
import { SaldosPanel } from "./estoque/SaldosPanel";

export function EstoquePage({ api }: { api: CatalogoApi }) {
  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Estoque</h1>
      <Card className="mt-4">
        <SaldosPanel api={api} />
      </Card>
    </section>
  );
}
