import type { SocketLike } from "../domain/TelemetriaCliente";

// Socket de mentira para os testes: o teste decide quando abre, recebe e cai.
export class SocketFalso implements SocketLike {
  onopen: ((evento: unknown) => void) | null = null;
  onmessage: ((evento: { data: unknown }) => void) | null = null;
  onclose: ((evento: unknown) => void) | null = null;
  onerror: ((evento: unknown) => void) | null = null;
  fechado = false;

  constructor(readonly url: string) {}

  close(): void {
    this.fechado = true;
  }

  abrir(): void {
    this.onopen?.({});
  }

  receber(corpo: unknown): void {
    this.onmessage?.({ data: typeof corpo === "string" ? corpo : JSON.stringify(corpo) });
  }

  cair(): void {
    this.onclose?.({});
  }
}

// `criar` entra no TelemetriaCliente; `sockets` guarda todos os sockets abertos, na ordem.
export function fabricaDeSockets() {
  const sockets: SocketFalso[] = [];
  const criar = (url: string): SocketFalso => {
    const socket = new SocketFalso(url);
    sockets.push(socket);
    return socket;
  };
  return { criar, sockets };
}
