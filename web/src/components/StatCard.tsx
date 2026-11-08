import type { ReactNode } from "react";

type Props = { label: string; value: ReactNode; caption?: string; variant?: "destaque" | "branco" };

const VARIANTS = {
  destaque: "bg-azul-500 text-branco",
  branco: "bg-branco text-tinta border border-neutro-100 shadow-card",
};

export function StatCard({ label, value, caption, variant = "destaque" }: Props) {
  return (
    <div className={`rounded-card p-5 ${VARIANTS[variant]}`}>
      <p className="text-sm">{label}</p>
      <p className="font-display text-4xl font-bold tabular-nums">{value}</p>
      {caption && <p className="text-xs">{caption}</p>}
    </div>
  );
}
