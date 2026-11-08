import { http, HttpResponse } from "msw";
import { ApiError } from "./ApiClient";
import { HttpApiClient } from "./HttpApiClient";
import { ME } from "./mocks/fixtures";
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
