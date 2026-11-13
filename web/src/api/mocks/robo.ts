import type { RobotState, Telemetry } from "../types";
import { TELEMETRIAS } from "./fixtures";

// Roteiro do modo demo: o robô passa pelos estados de uma entrega, 4 avanços (4 s) em cada.
const ROTEIRO: RobotState[] = ["IDLE", "CARREGANDO", "A_CAMINHO", "CHEGOU", "AGUARDANDO_RETIRADA", "VOLTANDO"];
const AVANCOS_POR_ESTADO = 4;

// Robô de mentira para o dev e os testes: a parada de emergência vence o roteiro.
export class RoboSimulado {
  #estop = false;
  #passo = 0;

  definirEstop(ativo: boolean): void {
    this.#estop = ativo;
  }

  reiniciar(): void {
    this.#estop = false;
    this.#passo = 0;
  }

  atual(): Telemetry {
    const estado: RobotState = this.#estop
      ? "PARADA_EMERGENCIA"
      : ROTEIRO[Math.floor(this.#passo / AVANCOS_POR_ESTADO) % ROTEIRO.length];
    return { ...TELEMETRIAS[estado], updated_at: new Date().toISOString() };
  }

  avancar(): Telemetry {
    this.#passo += 1;
    return this.atual();
  }
}

export const roboSimulado = new RoboSimulado();
