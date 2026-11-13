import type { Telemetry } from "../api/types";
import { Observavel } from "./Observavel";
import { atrasoDeReconexao, lerTelemetria } from "./telemetria";

// O pedaço de WebSocket que usamos: o teste troca por um socket falso (src/test/SocketFalso.ts).
export interface SocketLike {
  onopen: ((evento: unknown) => void) | null;
  onmessage: ((evento: { data: unknown }) => void) | null;
  onclose: ((evento: { code?: number }) => void) | null;
  onerror: ((evento: unknown) => void) | null;
  close(): void;
}

export type EstadoConexao = "conectando" | "conectado" | "reconectando" | "parado" | "sessao_expirada" | "desistiu";

// O servidor fecha com 1008 (violação de política) quando o token do ?token= é inválido ou expirou.
const FECHAMENTO_TOKEN_INVALIDO = 1008;
// Tentativas seguidas de reconexão sem conseguir abrir; passou disso, desiste e avisa.
const MAX_TENTATIVAS = 10;

export type EventoTelemetria =
  | { tipo: "telemetria"; dados: Telemetry }
  | { tipo: "conexao"; estado: EstadoConexao };

// OBSERVER: sujeito que mantém o WebSocket /ws/telemetry aberto (reconecta sozinho) e avisa os observers.
// A URL é uma função porque o token pode mudar entre uma tentativa e outra (ApiClient.telemetryStreamUrl).
export class TelemetriaCliente extends Observavel<EventoTelemetria> {
  readonly #urlDoStream: () => string;
  readonly #criarSocket: (url: string) => SocketLike;
  #socket: SocketLike | null = null;
  #timer: ReturnType<typeof setTimeout> | null = null;
  #tentativas = 0;
  #ativo = false;

  constructor(
    urlDoStream: () => string,
    criarSocket: (url: string) => SocketLike = (url) => new WebSocket(url) as unknown as SocketLike,
  ) {
    super();
    this.#urlDoStream = urlDoStream;
    this.#criarSocket = criarSocket;
  }

  iniciar(): void {
    if (this.#ativo) return;
    this.#ativo = true;
    this.#tentativas = 0;
    this.notificar({ tipo: "conexao", estado: "conectando" });
    this.#conectar();
  }

  parar(): void {
    this.#ativo = false;
    if (this.#timer !== null) {
      clearTimeout(this.#timer);
      this.#timer = null;
    }
    const socket = this.#socket;
    this.#socket = null;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
    }
    this.notificar({ tipo: "conexao", estado: "parado" });
  }

  #conectar(): void {
    let socket: SocketLike;
    try {
      socket = this.#criarSocket(this.#urlDoStream());
    } catch {
      this.#reagendar();
      return;
    }
    this.#socket = socket;
    socket.onopen = () => {
      this.#tentativas = 0;
      this.notificar({ tipo: "conexao", estado: "conectado" });
    };
    socket.onmessage = (evento) => {
      const dados = lerTelemetria(String(evento.data));
      if (dados) this.notificar({ tipo: "telemetria", dados });
    };
    socket.onclose = (evento) => {
      if (this.#socket !== socket) return;
      this.#socket = null;
      if (evento?.code === FECHAMENTO_TOKEN_INVALIDO) {
        this.#encerrar("sessao_expirada");
        return;
      }
      this.#reagendar();
    };
  }

  // Para de vez (sem religar em laço) e diz por quê.
  #encerrar(motivo: "sessao_expirada" | "desistiu"): void {
    this.#ativo = false;
    this.notificar({ tipo: "conexao", estado: motivo });
  }

  #reagendar(): void {
    if (this.#tentativas >= MAX_TENTATIVAS) {
      this.#encerrar("desistiu");
      return;
    }
    const espera = atrasoDeReconexao(this.#tentativas);
    this.#tentativas += 1;
    this.notificar({ tipo: "conexao", estado: "reconectando" });
    this.#timer = setTimeout(() => {
      this.#timer = null;
      this.#conectar();
    }, espera);
  }
}
