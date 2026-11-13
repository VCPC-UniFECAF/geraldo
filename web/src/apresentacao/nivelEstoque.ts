import { CircleAlert, TriangleAlert, type LucideIcon } from "lucide-react";

export type NivelId = "ok" | "atencao" | "abaixo";

// STRATEGY: cada nível sabe sua cor, seu texto e seu ícone (DS §3.5). Novo nível = nova classe (OCP).
export abstract class NivelEstoqueStrategy {
  abstract readonly valor: NivelId;
  abstract readonly barra: string;
  abstract readonly texto: string;
  abstract readonly rotulo: string | null;
  abstract readonly Icone: LucideIcon | null;
}

// STRATEGY: nível Normal.
class Normal extends NivelEstoqueStrategy {
  readonly valor = "ok";
  readonly barra = "bg-azul-500";
  readonly texto = "text-neutro-600";
  readonly rotulo = null;
  readonly Icone = null;
}

// STRATEGY: nível PertoDoMinimo.
class PertoDoMinimo extends NivelEstoqueStrategy {
  readonly valor = "atencao";
  readonly barra = "bg-aviso-500";
  readonly texto = "text-aviso-700";
  readonly rotulo = "Perto do mínimo";
  readonly Icone = CircleAlert;
}

// STRATEGY: nível AbaixoDoMinimo.
class AbaixoDoMinimo extends NivelEstoqueStrategy {
  readonly valor = "abaixo";
  readonly barra = "bg-vermelho-500";
  readonly texto = "text-vermelho-600";
  readonly rotulo = "Abaixo do mínimo";
  readonly Icone = TriangleAlert;
}

const NORMAL = new Normal();
const PERTO = new PertoDoMinimo();
const ABAIXO = new AbaixoDoMinimo();

// FACTORY: acima de 120% do mínimo = normal; de 100% a 120% = perto; abaixo do mínimo = abaixo.
export function nivelDe(quantidade: number, minimo: number): NivelEstoqueStrategy {
  if (minimo <= 0) return NORMAL; // sem mínimo configurado, nada a avisar
  if (quantidade < minimo) return ABAIXO;
  if (quantidade <= minimo * 1.2) return PERTO;
  return NORMAL;
}

// A barra enche até o dobro do mínimo (o mínimo fica no meio); sem mínimo, fica cheia.
export function preenchimento(quantidade: number, minimo: number): number {
  if (minimo <= 0) return 100;
  return Math.min(100, Math.round((quantidade / (minimo * 2)) * 100));
}
