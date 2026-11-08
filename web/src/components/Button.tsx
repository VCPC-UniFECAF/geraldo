import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primario" | "secundario" | "fantasma" | "perigo";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  primario: "bg-azul-500 text-branco hover:bg-azul-600",
  secundario: "bg-branco text-tinta border border-neutro-200 hover:bg-neutro-50",
  fantasma: "bg-transparent text-azul-600 hover:bg-azul-50",
  perigo: "bg-vermelho-500 text-branco hover:bg-vermelho-600",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "min-h-[36px] px-4 text-sm",
  md: "min-h-controle px-5 text-base",
  lg: "min-h-[52px] px-6 text-base",
};

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-controle font-sans font-semibold transition active:scale-[0.98] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-azul-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize };

export function Button({ variant = "primario", size = "md", className = "", type = "button", ...rest }: Props) {
  return <button type={type} className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`} {...rest} />;
}
