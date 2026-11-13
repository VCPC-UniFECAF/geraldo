import { Bot, Navigation, PackageCheck, PackagePlus, Siren, Undo2, type LucideIcon } from "lucide-react";
import type { RobotState } from "../api/types";

// STRATEGY: cada estado do robô sabe seu texto, cor e ícone (DS §3.5). Neutro: livre e carregando; azul: em movimento; vermelho: emergência.
export abstract class EstadoRoboStrategy {
  abstract readonly valor: RobotState;
  abstract readonly rotulo: string;
  abstract readonly caixa: string;
  abstract readonly Icone: LucideIcon;
  get emEmergencia(): boolean {
    return false;
  }
}

class Livre extends EstadoRoboStrategy {
  readonly valor = "IDLE";
  readonly rotulo = "Livre";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = Bot;
}

class Carregando extends EstadoRoboStrategy {
  readonly valor = "CARREGANDO";
  readonly rotulo = "Carregando";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = PackagePlus;
}

class ACaminho extends EstadoRoboStrategy {
  readonly valor = "A_CAMINHO";
  readonly rotulo = "A caminho";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = Navigation;
}

class Chegou extends EstadoRoboStrategy {
  readonly valor = "CHEGOU";
  readonly rotulo = "Chegou ao destino";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = PackageCheck;
}

class AguardandoRetirada extends EstadoRoboStrategy {
  readonly valor = "AGUARDANDO_RETIRADA";
  readonly rotulo = "Aguardando retirada";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = PackageCheck;
}

class Voltando extends EstadoRoboStrategy {
  readonly valor = "VOLTANDO";
  readonly rotulo = "Voltando à base";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = Undo2;
}

class ParadaEmergencia extends EstadoRoboStrategy {
  readonly valor = "PARADA_EMERGENCIA";
  readonly rotulo = "Parada de emergência";
  readonly caixa = "bg-vermelho-100 text-vermelho-700";
  readonly Icone = Siren;
  override get emEmergencia() {
    return true;
  }
}

const ESTADOS: readonly EstadoRoboStrategy[] = [
  new Livre(),
  new Carregando(),
  new ACaminho(),
  new Chegou(),
  new AguardandoRetirada(),
  new Voltando(),
  new ParadaEmergencia(),
];

// FACTORY: devolve a estratégia do estado recebido na telemetria.
export function estadoRoboDe(valor: RobotState): EstadoRoboStrategy {
  const estrategia = ESTADOS.find((e) => e.valor === valor);
  if (!estrategia) throw new Error(`Estado do robô desconhecido: ${valor}`);
  return estrategia;
}
