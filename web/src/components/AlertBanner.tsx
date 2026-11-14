import { Info, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Variante = "perigo" | "info";

const VARIANTES: Record<Variante, { caixa: string; Icone: LucideIcon; role: "alert" | "status" }> = {
  perigo: { caixa: "border-vermelho-200 bg-vermelho-50 text-vermelho-600", Icone: TriangleAlert, role: "alert" },
  info: { caixa: "border-azul-200 bg-azul-50 text-azul-700", Icone: Info, role: "status" },
};

// `alert` já é aria-live assertivo (parada de emergência); `status` é educado (DS §8).
export function AlertBanner({ variante = "perigo", children }: { variante?: Variante; children: ReactNode }) {
  const { caixa, Icone, role } = VARIANTES[variante];
  return (
    <div role={role} className={`flex items-start gap-2 rounded-controle border px-3 py-3 text-sm ${caixa}`}>
      <Icone size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
