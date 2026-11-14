import { ApiError, type ApiClient } from "./ApiClient";
import type { Delivery, DeliveryCreate, EstopState, Location, Me, Movement, MovementFiltro, StockEntry, Telemetry } from "./types";

export class HttpApiClient implements ApiClient {
  #token: string | null = null;
  readonly #baseUrl: string;

  constructor(baseUrl: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000") {
    this.#baseUrl = baseUrl;
  }

  definirToken(token: string | null): void {
    this.#token = token;
  }

  async #request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (init.body) headers.set("Content-Type", "application/json");
    if (this.#token) headers.set("Authorization", `Bearer ${this.#token}`);
    const res = await fetch(`${this.#baseUrl}${path}`, { ...init, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? "Algo deu errado. Tente de novo.");
    }
    return (res.status === 204 ? undefined : await res.json()) as T;
  }

  login(username: string, password: string) {
    return this.#request<{ access_token: string; token_type: "bearer" }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  }

  me() {
    return this.#request<Me>("/me");
  }

  locations() {
    return this.#request<Location[]>("/locations");
  }

  stock(locationId?: string) {
    return this.#request<StockEntry[]>(`/stock${locationId ? `?location_id=${encodeURIComponent(locationId)}` : ""}`);
  }

  createDelivery(body: DeliveryCreate) {
    return this.#request<Delivery>("/deliveries", { method: "POST", body: JSON.stringify(body) });
  }

  deliveries() {
    return this.#request<Delivery[]>("/deliveries");
  }

  confirmReceipt(id: number) {
    return this.#request<Delivery>(`/deliveries/${id}/confirm-receipt`, { method: "POST" });
  }

  movements(filtro: MovementFiltro = {}) {
    const query = new URLSearchParams();
    if (filtro.deliveryId !== undefined) query.set("delivery_id", String(filtro.deliveryId));
    if (filtro.locationId) query.set("location_id", filtro.locationId);
    const texto = query.toString();
    return this.#request<Movement[]>(`/movements${texto ? `?${texto}` : ""}`);
  }

  telemetry() {
    return this.#request<Telemetry>("/telemetry");
  }

  setEstop(active: boolean) {
    const corpo: EstopState = { active };
    return this.#request<void>("/robot/estop", { method: "POST", body: JSON.stringify(corpo) });
  }

  telemetryStreamUrl() {
    const url = `${this.#baseUrl.replace(/^http/, "ws")}/ws/telemetry`;
    return this.#token ? `${url}?token=${encodeURIComponent(this.#token)}` : url;
  }
}
