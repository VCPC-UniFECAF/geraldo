import { Bot, CircleHelp, Navigation, PackageCheck, PackagePlus, Siren, Undo2, type LucideIcon } from "lucide-react";
import type { RobotState } from "../api/types";

// STRATEGY: cada estado do robô sabe seu texto, cor e ícone (DS §3.5). Neutro: livre e carregando; azul: em movimento; vermelho: emergência.
export abstract class EstadoRoboStrategy {
  abstract readonly valor: RobotState | "DESCONHECIDO";
  abstract readonly rotulo: string;
  abstract readonly caixa: string;
  abstract readonly Icone: LucideIcon;
  get emEmergencia(): boolean {
    return false;
  }
}

// STRATEGY: estado Livre.
class Livre extends EstadoRoboStrategy {
  readonly valor = "IDLE";
  readonly rotulo = "Livre";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = Bot;
}

// STRATEGY: estado Carregando.
class Carregando extends EstadoRoboStrategy {
  readonly valor = "CARREGANDO";
  readonly rotulo = "Carregando";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = PackagePlus;
}

// STRATEGY: estado ACaminho.
class ACaminho extends EstadoRoboStrategy {
  readonly valor = "A_CAMINHO";
  readonly rotulo = "A caminho";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = Navigation;
}

// STRATEGY: estado Chegou.
class Chegou extends EstadoRoboStrategy {
  readonly valor = "CHEGOU";
  readonly rotulo = "Chegou ao destino";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = PackageCheck;
}

// STRATEGY: estado AguardandoRetirada.
class AguardandoRetirada extends EstadoRoboStrategy {
  readonly valor = "AGUARDANDO_RETIRADA";
  readonly rotulo = "Aguardando retirada";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = PackageCheck;
}

// STRATEGY: estado Voltando.
class Voltando extends EstadoRoboStrategy {
  readonly valor = "VOLTANDO";
  readonly rotulo = "Voltando à base";
  readonly caixa = "bg-azul-100 text-azul-700";
  readonly Icone = Undo2;
}

// STRATEGY: estado ParadaEmergencia.
class ParadaEmergencia extends EstadoRoboStrategy {
  readonly valor = "PARADA_EMERGENCIA";
  readonly rotulo = "Parada de emergência";
  readonly caixa = "bg-vermelho-100 text-vermelho-700";
  readonly Icone = Siren;
  override get emEmergencia() {
    return true;
  }
}

// Fallback neutro para um estado que o contrato ainda não tem aqui (ex.: snapshot de uma versão nova do backend).
// STRATEGY: estado Desconhecido.
class Desconhecido extends EstadoRoboStrategy {
  readonly valor = "DESCONHECIDO";
  readonly rotulo = "Estado desconhecido";
  readonly caixa = "bg-neutro-50 text-neutro-600";
  readonly Icone = CircleHelp;
}

const DESCONHECIDO = new Desconhecido();
const ESTADOS: readonly EstadoRoboStrategy[] = [
  new Livre(),
  new Carregando(),
  new ACaminho(),
  new Chegou(),
  new AguardandoRetirada(),
  new Voltando(),
  new ParadaEmergencia(),
];

// FACTORY: devolve a estratégia do estado recebido na telemetria (ou o fallback neutro).
export function estadoRoboDe(valor: RobotState): EstadoRoboStrategy {
  return ESTADOS.find((e) => e.valor === valor) ?? DESCONHECIDO;
}
