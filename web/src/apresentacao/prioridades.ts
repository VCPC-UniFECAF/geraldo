import type { Priority } from "../api/types";

// STRATEGY: cada prioridade sabe como se apresentar e se tem aviso. Nova prioridade = nova classe (OCP).
export abstract class PrioridadeStrategy {
  abstract readonly valor: Priority;
  abstract readonly rotulo: string;
  abstract readonly caixa: string;
  abstract readonly ponto: string;
  get aviso(): string | null {
    return null;
  }
}

class Critica extends PrioridadeStrategy {
  readonly valor = "critica";
  readonly rotulo = "Crítica";
  readonly caixa = "bg-vermelho-100 text-vermelho-700";
  readonly ponto = "bg-vermelho-500";
  override get aviso() {
    return "Prioridade crítica exige a assinatura do farmacêutico.";
  }
}

class Media extends PrioridadeStrategy {
  readonly valor = "media";
  readonly rotulo = "Média";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly ponto = "bg-azul-500";
}

class Rotina extends PrioridadeStrategy {
  readonly valor = "rotina";
  readonly rotulo = "Rotina";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly ponto = "bg-neutro-400";
}

export const PRIORIDADES: readonly PrioridadeStrategy[] = [new Critica(), new Media(), new Rotina()];

// FACTORY: devolve a estratégia certa para o valor que veio do backend.
export function prioridadeDe(valor: Priority): PrioridadeStrategy {
  const estrategia = PRIORIDADES.find((p) => p.valor === valor);
  if (!estrategia) throw new Error(`Prioridade desconhecida: ${valor}`);
  return estrategia;
}
