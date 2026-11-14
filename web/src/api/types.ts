// Espelha docs/contracts/openapi.yaml. Mudança de contrato só por PR com aviso ao Samuel.
export type Priority = "critica" | "media" | "rotina";
export type Role = "medico" | "enfermeiro" | "farmaceutico" | "admin" | "robo";
export type DeliveryStatus =
  | "PENDENTE_APROVACAO"
  | "NA_FILA"
  | "EM_ROTA"
  | "AGUARDANDO_RECEBIMENTO"
  | "ENTREGUE"
  | "CANCELADA"
  | "FALHOU";

export interface Me {
  id: number;
  username: string;
  role: Role;
  local_id: string | null;
}

export interface Location {
  id: string;
  name: string;
  kind: string;
  has_stock: boolean;
  waypoint: string | null;
}

export interface StockEntry {
  location_id: string;
  item_id: string;
  item_name: string;
  quantity: number;
  reserved: number;
  minimum: number;
}

export interface DeliveryItem {
  item_id: string;
  quantity: number;
}

export interface DeliveryCreate {
  origin_id: string;
  dest_id?: string | null;
  items: DeliveryItem[];
  priority: Priority;
}

export interface Delivery {
  id: number;
  origin_id: string;
  dest_id: string;
  items: DeliveryItem[];
  priority: Priority;
  status: DeliveryStatus;
  requested_by: number;
  created_at: string;
}

export type MovementType = "RESERVA" | "BAIXA" | "CREDITO" | "ESTORNO";

export interface Movement {
  id: number;
  delivery_id?: number | null;
  type: MovementType;
  item_id: string;
  location_id: string;
  quantity: number;
  created_at: string;
}

export interface MovementFiltro {
  deliveryId?: number;
  locationId?: string;
}

export const ROBOT_STATES = [
  "IDLE",
  "CARREGANDO",
  "A_CAMINHO",
  "CHEGOU",
  "AGUARDANDO_RETIRADA",
  "VOLTANDO",
  "PARADA_EMERGENCIA",
] as const;
export type RobotState = (typeof ROBOT_STATES)[number];

// Coordenadas em metros no referencial `map` do robô.
export interface Ponto {
  x: number;
  y: number;
}

export interface Obstaculo extends Ponto {
  radius: number;
}

export interface Telemetry {
  robot_state: RobotState;
  pose: { x: number; y: number; yaw: number };
  battery: number;
  delivery_id?: number | null;
  route?: Ponto[];
  obstacles?: Obstaculo[];
  updated_at: string;
}

export interface EstopState {
  active: boolean;
}
