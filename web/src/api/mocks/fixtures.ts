import exemplos from "../../../../docs/contracts/examples/robot-telemetry.json";
import type { Delivery, Location, Me, Movement, RobotState, StockEntry, Telemetry } from "../types";

export const ME: Me = { id: 1, username: "medico1", role: "medico", local_id: "consultorio1" };
export const FARMACEUTICO: Me = { id: 2, username: "farmaceutico1", role: "farmaceutico", local_id: "farmacia" };
export const ADMIN: Me = { id: 3, username: "admin", role: "admin", local_id: null };

// O mock de login escolhe o usuário pelo nome (senha sempre "demo").
export const USUARIOS: Record<string, Me> = { medico1: ME, farmaceutico1: FARMACEUTICO, admin: ADMIN };

export const LOCATIONS: Location[] = [
  { id: "farmacia", name: "Farmácia central", kind: "pharmacy", has_stock: true, waypoint: "farmacia_balcao" },
  { id: "banco_sangue", name: "Banco de sangue", kind: "blood_bank", has_stock: true, waypoint: "banco_sangue_retirada" },
  { id: "consultorio1", name: "Consultório 1", kind: "office", has_stock: true, waypoint: "cons1_entrega" },
  { id: "consultorio2", name: "Consultório 2", kind: "office", has_stock: true, waypoint: "cons2_entrega" },
  { id: "enfermaria214", name: "Enfermaria 214", kind: "ward", has_stock: true, waypoint: "enf214_entrega" },
  { id: "recepcao", name: "Recepção", kind: "reception", has_stock: false, waypoint: null },
];

export const STOCK: StockEntry[] = [
  { location_id: "farmacia", item_id: "dipirona-500mg", item_name: "Dipirona 500 mg", quantity: 420, reserved: 0, minimum: 100 },
  { location_id: "farmacia", item_id: "amoxicilina-500mg", item_name: "Amoxicilina 500 mg", quantity: 200, reserved: 200, minimum: 60 },
  { location_id: "banco_sangue", item_id: "bolsa-sangue-o-neg", item_name: "Bolsa de sangue O negativo", quantity: 6, reserved: 0, minimum: 10 },
];

export const DELIVERY: Delivery = {
  id: 1,
  origin_id: "farmacia",
  dest_id: "consultorio1",
  items: [{ item_id: "dipirona-500mg", quantity: 5 }],
  priority: "media",
  status: "EM_ROTA",
  requested_by: 1,
  created_at: "2026-11-09T13:20:00Z",
};

export const DELIVERY_AGUARDANDO: Delivery = { ...DELIVERY, id: 2, status: "AGUARDANDO_RECEBIMENTO" };

export const MOVEMENTS: Movement[] = [
  { id: 1, delivery_id: 1, type: "RESERVA", item_id: "dipirona-500mg", location_id: "farmacia", quantity: 5, created_at: "2026-11-09T13:20:00Z" },
  { id: 2, delivery_id: 1, type: "BAIXA", item_id: "dipirona-500mg", location_id: "farmacia", quantity: 5, created_at: "2026-11-09T13:22:00Z" },
  { id: 3, delivery_id: 1, type: "CREDITO", item_id: "dipirona-500mg", location_id: "consultorio1", quantity: 5, created_at: "2026-11-09T13:30:00Z" },
  { id: 4, delivery_id: 3, type: "ESTORNO", item_id: "bolsa-sangue-o-neg", location_id: "banco_sangue", quantity: 2, created_at: "2026-11-09T14:00:00Z" },
];

// Um corpo de telemetria por estado, gerado do código do robô (docs/contracts/examples/robot-telemetry.json).
export const TELEMETRIAS = exemplos as unknown as Record<RobotState, Telemetry>;
