import { http, HttpResponse } from "msw";
import type { Delivery, DeliveryCreate } from "../types";
import { LOCATIONS, ME, STOCK } from "./fixtures";

const BASE = "http://localhost:8000";

// Estado em memória: no modo demo, o que você solicita aparece em "Minhas entregas".
let entregas: Delivery[] = [];

export function reiniciarMocks(): void {
  entregas = [];
}

export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const { password } = (await request.json()) as { username: string; password: string };
    if (password !== "demo") {
      return HttpResponse.json({ detail: "Usuário ou senha incorretos. Tente de novo." }, { status: 401 });
    }
    return HttpResponse.json({ access_token: "token-de-teste", token_type: "bearer" });
  }),
  http.get(`${BASE}/me`, () => HttpResponse.json(ME)),
  http.get(`${BASE}/locations`, () => HttpResponse.json(LOCATIONS)),
  http.get(`${BASE}/stock`, ({ request }) => {
    const locationId = new URL(request.url).searchParams.get("location_id");
    return HttpResponse.json(locationId ? STOCK.filter((s) => s.location_id === locationId) : STOCK);
  }),
  http.post(`${BASE}/deliveries`, async ({ request }) => {
    const body = (await request.json()) as DeliveryCreate;
    const entrega: Delivery = {
      id: entregas.length + 1,
      origin_id: body.origin_id,
      dest_id: body.dest_id ?? ME.local_id ?? "",
      items: body.items,
      priority: body.priority,
      status: body.priority === "critica" ? "PENDENTE_APROVACAO" : "NA_FILA",
      requested_by: ME.id,
      created_at: new Date().toISOString(),
    };
    entregas.push(entrega);
    return HttpResponse.json(entrega, { status: 201 });
  }),
  http.get(`${BASE}/deliveries`, () => HttpResponse.json(entregas)),
];
