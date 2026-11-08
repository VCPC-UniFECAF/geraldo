import type { Delivery, DeliveryCreate, Location, Me, StockEntry } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

// ISP: cada tela depende só do pedaço da API que usa.
export interface SessaoApi {
  login(username: string, password: string): Promise<{ access_token: string; token_type: "bearer" }>;
  me(): Promise<Me>;
  definirToken(token: string | null): void;
}

export interface CatalogoApi {
  locations(): Promise<Location[]>;
  stock(locationId?: string): Promise<StockEntry[]>;
}

export interface EntregasApi {
  createDelivery(body: DeliveryCreate): Promise<Delivery>;
  deliveries(): Promise<Delivery[]>;
}

// DIP: a aplicação conhece essa abstração; quem fala HTTP é a HttpApiClient.
export type ApiClient = SessaoApi & CatalogoApi & EntregasApi;
