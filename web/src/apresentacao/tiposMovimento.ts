import { ArrowLeftRight, Lock, PackageMinus, PackagePlus, Undo2, type LucideIcon } from "lucide-react";
import type { MovementType } from "../api/types";

// STRATEGY: cada tipo de movimentação sabe seu texto, o sinal da quantidade, a cor e o ícone. A quantidade do contrato é sempre positiva.
export abstract class TipoMovimentoStrategy {
  abstract readonly valor: MovementType;
  abstract readonly rotulo: string;
  abstract readonly sinal: "+" | "-";
  abstract readonly caixa: string;
  abstract readonly Icone: LucideIcon;
}

// STRATEGY
class Reserva extends TipoMovimentoStrategy {
  readonly valor = "RESERVA";
  readonly rotulo = "Reserva";
  readonly sinal = "-";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = Lock;
}

// STRATEGY
class Baixa extends TipoMovimentoStrategy {
  readonly valor = "BAIXA";
  readonly rotulo = "Baixa";
  readonly sinal = "-";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = PackageMinus;
}

// STRATEGY
class Credito extends TipoMovimentoStrategy {
  readonly valor = "CREDITO";
  readonly rotulo = "Crédito";
  readonly sinal = "+";
  readonly caixa = "bg-sucesso-50 text-sucesso-700";
  readonly Icone = PackagePlus;
}

// STRATEGY
class Estorno extends TipoMovimentoStrategy {
  readonly valor = "ESTORNO";
  readonly rotulo = "Estorno";
  readonly sinal = "+";
  readonly caixa = "bg-aviso-50 text-aviso-700";
  readonly Icone = Undo2;
}

// STRATEGY: fallback neutro para um tipo que o backend ainda não conhecemos aqui.
class Outro extends TipoMovimentoStrategy {
  readonly valor = "OUTRO" as MovementType;
  readonly rotulo = "Movimentação";
  readonly sinal = "+";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = ArrowLeftRight;
}

const OUTRO = new Outro();
const TIPOS: readonly TipoMovimentoStrategy[] = [new Reserva(), new Baixa(), new Credito(), new Estorno()];

// FACTORY: devolve a estratégia do tipo recebido (ou o fallback neutro).
export function tipoMovimentoDe(valor: MovementType): TipoMovimentoStrategy {
  return TIPOS.find((t) => t.valor === valor) ?? OUTRO;
}
