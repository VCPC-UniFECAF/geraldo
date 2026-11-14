import { http, HttpResponse } from "msw";
import { ApiError } from "./ApiClient";
import { HttpApiClient } from "./HttpApiClient";
import { DELIVERY, DELIVERY_AGUARDANDO, ME } from "./mocks/fixtures";
import { semearEntregas } from "./mocks/handlers";
import { server } from "./mocks/server";

const api = new HttpApiClient();

afterEach(() => api.definirToken(null));

test("login devolve o token", async () => {
  const res = await api.login("medico1", "demo");
  expect(res.access_token).toBe("token-de-teste");
});

test("login com senha errada levanta ApiError com a mensagem da API", async () => {
  await expect(api.login("medico1", "errada")).rejects.toMatchObject({
    status: 401,
    message: "Usuário ou senha incorretos. Tente de novo.",
  });
});

test("envia o token no cabeçalho Authorization", async () => {
  let header: string | null = null;
  server.use(
    http.get("http://localhost:8000/me", ({ request }) => {
      header = request.headers.get("authorization");
      return HttpResponse.json(ME);
    }),
  );
  api.definirToken("abc");
  await api.me();
  expect(header).toBe("Bearer abc");
});

test("stock filtra por local", async () => {
  const entries = await api.stock("farmacia");
  expect(entries.length).toBeGreaterThan(0);
  expect(entries.every((e) => e.location_id === "farmacia")).toBe(true);
});

test("createDelivery manda o corpo e devolve a entrega criada", async () => {
  const delivery = await api.createDelivery({
    origin_id: "farmacia",
    dest_id: null,
    items: [{ item_id: "dipirona-500mg", quantity: 5 }],
    priority: "media",
  });
  expect(delivery).toMatchObject({ origin_id: "farmacia", dest_id: "consultorio1", status: "NA_FILA", priority: "media" });
});

test("erro sem corpo JSON vira ApiError com mensagem padrão", async () => {
  server.use(http.get("http://localhost:8000/locations", () => new HttpResponse("falhou", { status: 500 })));
  const err = await api.locations().catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(500);
  expect(err.message).toBe("Algo deu errado. Tente de novo.");
});

test("confirmReceipt confirma a entrega que aguarda recebimento e credita o destino", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  const entrega = await api.confirmReceipt(2);
  expect(entrega.status).toBe("ENTREGUE");
  const movimentos = await api.movements({ deliveryId: 2 });
  expect(movimentos).toMatchObject([{ type: "CREDITO", location_id: "consultorio1", quantity: 5 }]);
});

test("confirmReceipt de entrega que ainda está a caminho levanta ApiError 409", async () => {
  semearEntregas([DELIVERY]);
  await expect(api.confirmReceipt(1)).rejects.toMatchObject({
    status: 409,
    message: "A entrega ainda não chegou ao destino. Aguarde o robô.",
  });
});

test("movements filtra por local", async () => {
  const lista = await api.movements({ locationId: "banco_sangue" });
  expect(lista.map((m) => m.id)).toEqual([4]);
});

test("telemetry devolve o último estado do robô", async () => {
  const telemetria = await api.telemetry();
  expect(telemetria.robot_state).toBe("IDLE");
  expect(telemetria.pose).toEqual({ x: 6.5, y: 26.5, yaw: -1.5708 });
});

test("setEstop recusa quem não é administrador nem farmacêutico", async () => {
  await expect(api.setEstop(true)).rejects.toMatchObject({
    status: 403,
    message: "Só administrador e farmacêutico acionam a parada de emergência.",
  });
});

test("setEstop liga e desliga a parada e a telemetria acompanha", async () => {
  await api.login("farmaceutico1", "demo");
  expect((await api.me()).role).toBe("farmaceutico");
  await api.setEstop(true);
  expect((await api.telemetry()).robot_state).toBe("PARADA_EMERGENCIA");
  await api.setEstop(false);
  expect((await api.telemetry()).robot_state).toBe("IDLE");
});

test("telemetryStreamUrl troca http por ws e leva o token quando há login", () => {
  expect(api.telemetryStreamUrl()).toBe("ws://localhost:8000/ws/telemetry");
  api.definirToken("abc");
  expect(api.telemetryStreamUrl()).toBe("ws://localhost:8000/ws/telemetry?token=abc");
});
