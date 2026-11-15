import type { AprovacoesApi, CatalogoApi, EntregasApi, HistoricoApi } from "../api/ApiClient";
import type { Role } from "../api/types";
import { AprovacoesPanel } from "./AprovacoesPanel";
import { EstoquePage } from "./EstoquePage";

// Só farmacêutico e admin chegam aqui (o AppShell esconde a aba dos outros papéis).
export function FarmaciaPage({ api, role }: { api: CatalogoApi & HistoricoApi & EntregasApi & AprovacoesApi; role: Role }) {
  return (
    <div className="grid gap-8">
      <h1 className="font-display text-2xl font-bold">Farmácia</h1>
      <AprovacoesPanel api={api} role={role} />
      <EstoquePage api={api} />
    </div>
  );
}
