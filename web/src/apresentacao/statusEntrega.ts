import { Ban, Bot, CircleCheck, Clock, PackageCheck, ShieldCheck, TriangleAlert, type LucideIcon } from "lucide-react";
import type { DeliveryStatus } from "../api/types";

// STRATEGY: cada status sabe seu texto, cor, ícone e se aparece riscado.
export abstract class StatusStrategy {
  abstract readonly valor: DeliveryStatus;
  abstract readonly rotulo: string;
  abstract readonly caixa: string;
  abstract readonly Icone: LucideIcon;
  get riscado(): boolean {
    return false;
  }
}

class PendenteAprovacao extends StatusStrategy {
  readonly valor = "PENDENTE_APROVACAO";
  readonly rotulo = "Aguardando aprovação";
  readonly caixa = "bg-aviso-50 text-aviso-700";
  readonly Icone = ShieldCheck;
}

class NaFila extends StatusStrategy {
  readonly valor = "NA_FILA";
  readonly rotulo = "Na fila";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = Clock;
}

class EmRota extends StatusStrategy {
  readonly valor = "EM_ROTA";
  readonly rotulo = "A caminho";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = Bot;
}

class AguardandoRecebimento extends StatusStrategy {
  readonly valor = "AGUARDANDO_RECEBIMENTO";
  readonly rotulo = "Aguardando recebimento";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = PackageCheck;
}

class Entregue extends StatusStrategy {
  readonly valor = "ENTREGUE";
  readonly rotulo = "Entregue";
  readonly caixa = "bg-sucesso-50 text-sucesso-700";
  readonly Icone = CircleCheck;
}

class Cancelada extends StatusStrategy {
  readonly valor = "CANCELADA";
  readonly rotulo = "Cancelada";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = Ban;
  override get riscado() {
    return true;
  }
}

class Falhou extends StatusStrategy {
  readonly valor = "FALHOU";
  readonly rotulo = "Falhou";
  readonly caixa = "bg-vermelho-100 text-vermelho-700";
  readonly Icone = TriangleAlert;
}

const STATUS: readonly StatusStrategy[] = [
  new PendenteAprovacao(),
  new NaFila(),
  new EmRota(),
  new AguardandoRecebimento(),
  new Entregue(),
  new Cancelada(),
  new Falhou(),
];

// FACTORY: devolve a estratégia do status recebido.
export function statusDe(valor: DeliveryStatus): StatusStrategy {
  const estrategia = STATUS.find((s) => s.valor === valor);
  if (!estrategia) throw new Error(`Status desconhecido: ${valor}`);
  return estrategia;
}
