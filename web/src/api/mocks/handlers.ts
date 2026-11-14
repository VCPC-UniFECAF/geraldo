import { http, HttpResponse } from "msw";
import type { Delivery, DeliveryCreate, Me, Movement } from "../types";
import { LOCATIONS, ME, MOVEMENTS, STOCK, USUARIOS } from "./fixtures";
import { roboSimulado } from "./robo";

const BASE = "http://localhost:8000";
const PAPEIS_DE_EMERGENCIA = ["admin", "farmaceutico"];

// Estado em memória: no modo demo, o que você solicita aparece em "Minhas entregas".
let entregas: Delivery[] = [];
let movimentos: Movement[] = [...MOVEMENTS];
let usuario: Me = ME;

export function reiniciarMocks(): void {
  entregas = [];
  movimentos = [...MOVEMENTS];
  usuario = ME;
  roboSimulado.reiniciar();
}

// Para testes: cópia, porque o handler de confirmação altera o status.
export function semearEntregas(lista: Delivery[]): void {
  entregas = lista.map((e) => ({ ...e }));
}

export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const { username, password } = (await request.json()) as { username: string; password: string };
    if (password !== "demo") {
      return HttpResponse.json({ detail: "Usuário ou senha incorretos. Tente de novo." }, { status: 401 });
    }
    usuario = USUARIOS[username] ?? ME;
    return HttpResponse.json({ access_token: "token-de-teste", token_type: "bearer" });
  }),
  http.get(`${BASE}/me`, () => HttpResponse.json(usuario)),
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
      dest_id: body.dest_id ?? usuario.local_id ?? "",
      items: body.items,
      priority: body.priority,
      status: body.priority === "critica" ? "PENDENTE_APROVACAO" : "NA_FILA",
      requested_by: usuario.id,
      created_at: new Date().toISOString(),
    };
    entregas.push(entrega);
    return HttpResponse.json(entrega, { status: 201 });
  }),
  http.get(`${BASE}/deliveries`, () => HttpResponse.json(entregas)),
  http.post(`${BASE}/deliveries/:id/confirm-receipt`, ({ params }) => {
    const entrega = entregas.find((e) => e.id === Number(params.id));
    if (!entrega) return HttpResponse.json({ detail: "Entrega não encontrada. Atualize a lista." }, { status: 404 });
    if (entrega.status !== "AGUARDANDO_RECEBIMENTO") {
      return HttpResponse.json({ detail: "A entrega ainda não chegou ao destino. Aguarde o robô." }, { status: 409 });
    }
    entrega.status = "ENTREGUE";
    for (const item of entrega.items) {
      movimentos.push({
        id: movimentos.length + 1,
        delivery_id: entrega.id,
        type: "CREDITO",
        item_id: item.item_id,
        location_id: entrega.dest_id,
        quantity: item.quantity,
        created_at: new Date().toISOString(),
      });
    }
    return HttpResponse.json(entrega);
  }),
  http.get(`${BASE}/movements`, ({ request }) => {
    const params = new URL(request.url).searchParams;
    const deliveryId = params.get("delivery_id");
    const locationId = params.get("location_id");
    return HttpResponse.json(
      movimentos.filter(
        (m) => (deliveryId === null || m.delivery_id === Number(deliveryId)) && (locationId === null || m.location_id === locationId),
      ),
    );
  }),
  http.get(`${BASE}/telemetry`, () => HttpResponse.json(roboSimulado.atual())),
  http.post(`${BASE}/robot/estop`, async ({ request }) => {
    if (!PAPEIS_DE_EMERGENCIA.includes(usuario.role)) {
      return HttpResponse.json({ detail: "Só administrador e farmacêutico acionam a parada de emergência." }, { status: 403 });
    }
    const corpo = (await request.json()) as { active?: unknown };
    if (typeof corpo.active !== "boolean") {
      return HttpResponse.json({ detail: "Informe se a parada de emergência deve ficar ativa." }, { status: 422 });
    }
    roboSimulado.definirEstop(corpo.active);
    return new HttpResponse(null, { status: 204 });
  }),
];
