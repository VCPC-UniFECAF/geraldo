import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-card border border-neutro-100 bg-branco p-4 shadow-card md:p-5 ${className}`} {...rest} />;
}
