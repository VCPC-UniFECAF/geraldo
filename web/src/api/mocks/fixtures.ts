import type { Delivery, Location, Me, StockEntry } from "../types";

export const ME: Me = { id: 1, username: "medico1", role: "medico", local_id: "consultorio1" };

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
