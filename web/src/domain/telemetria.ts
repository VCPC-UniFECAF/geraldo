// PROGRAMAÇÃO FUNCIONAL: funções puras sobre o corpo de telemetria do contrato.
import { ROBOT_STATES, type Ponto, type RobotState, type Telemetry } from "../api/types";

// Velocidade do robô decidida na semana 3 (3,0 m/s sempre); só serve para a estimativa de chegada.
export const VELOCIDADE_DO_ROBO = 3.0;

const LIMITE_DA_BATERIA_BAIXA = 20;

// ADAPTER: converte o texto cru de uma mensagem do WebSocket no tipo Telemetry do app.
// Valida o texto de uma mensagem do WebSocket. Devolve null se não for uma telemetria do contrato.
export function lerTelemetria(texto: string): Telemetry | null {
  let corpo: unknown;
  try {
    corpo = JSON.parse(texto);
  } catch {
    return null;
  }
  if (typeof corpo !== "object" || corpo === null) return null;
  const c = corpo as Partial<Telemetry>;
  const pose = c.pose;
  if (!ROBOT_STATES.includes(c.robot_state as RobotState)) return null;
  if (!pose || typeof pose.x !== "number" || typeof pose.y !== "number" || typeof pose.yaw !== "number") return null;
  if (typeof c.battery !== "number") return null;
  return {
    robot_state: c.robot_state as RobotState,
    pose,
    battery: c.battery,
    delivery_id: c.delivery_id ?? null,
    route: Array.isArray(c.route) ? c.route : [],
    obstacles: Array.isArray(c.obstacles) ? c.obstacles : [],
    updated_at: String(c.updated_at ?? ""),
  };
}

// Espera antes de reconectar: 1 s, 2 s, 4 s, 8 s e no máximo 10 s.
export const atrasoDeReconexao = (tentativa: number): number => Math.min(1000 * 2 ** tentativa, 10000);

export const comprimentoDaRota = (rota: Ponto[]): number =>
  rota.slice(1).reduce((total, ponto, i) => total + Math.hypot(ponto.x - rota[i].x, ponto.y - rota[i].y), 0);

export function segundosAteChegar(rota: Ponto[] | undefined, velocidade: number = VELOCIDADE_DO_ROBO): number | null {
  const metros = comprimentoDaRota(rota ?? []);
  return metros > 0 ? Math.ceil(metros / velocidade) : null;
}

export const bateriaBaixa = (bateria: number): boolean => bateria < LIMITE_DA_BATERIA_BAIXA;

// O backend responde 1970 antes do primeiro POST do robô; um robô que parou de postar fica com a data velha.
const ANO_2000 = Date.parse("2000-01-01T00:00:00Z");
export function semSinal(t: Telemetry, agora: number, limiteMs = 10_000): boolean {
  const quando = Date.parse(t.updated_at);
  return Number.isNaN(quando) || quando < ANO_2000 || agora - quando > limiteMs;
}
