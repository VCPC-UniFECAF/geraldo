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
