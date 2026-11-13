import { TELEMETRIAS } from "../api/mocks/fixtures";
import { fabricaDeSockets, SocketFalso } from "../test/SocketFalso";
import { TelemetriaCliente, type EventoTelemetria } from "./TelemetriaCliente";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

function montar() {
  const { criar, sockets } = fabricaDeSockets();
  const eventos: EventoTelemetria[] = [];
  const cliente = new TelemetriaCliente(() => "ws://teste/ws/telemetry", criar);
  cliente.adicionarObserver({ atualizar: (e) => eventos.push(e) });
  return { cliente, sockets, eventos };
}

const estados = (eventos: EventoTelemetria[]) => eventos.flatMap((e) => (e.tipo === "conexao" ? [e.estado] : []));

test("iniciar abre o socket na URL pedida e avisa conectando, depois conectado", () => {
  const { cliente, sockets, eventos } = montar();
  cliente.iniciar();
  expect(sockets.map((s) => s.url)).toEqual(["ws://teste/ws/telemetry"]);
  sockets[0].abrir();
  expect(estados(eventos)).toEqual(["conectando", "conectado"]);
});

test("cada mensagem válida vira um evento de telemetria; lixo é ignorado", () => {
  const { cliente, sockets, eventos } = montar();
  cliente.iniciar();
  sockets[0].abrir();
  sockets[0].receber(TELEMETRIAS.A_CAMINHO);
  sockets[0].receber("não é JSON");
  sockets[0].receber({ robot_state: "VOANDO" });
  expect(eventos.filter((e) => e.tipo === "telemetria")).toEqual([{ tipo: "telemetria", dados: TELEMETRIAS.A_CAMINHO }]);
});

test("iniciar duas vezes não abre dois sockets", () => {
  const { cliente, sockets } = montar();
  cliente.iniciar();
  cliente.iniciar();
  expect(sockets).toHaveLength(1);
});

test("quando a conexão cai, reconecta com espera crescente e zera a espera depois de conectar", () => {
  const { cliente, sockets, eventos } = montar();
  cliente.iniciar();
  sockets[0].cair();
  expect(estados(eventos)).toEqual(["conectando", "reconectando"]);
  vi.advanceTimersByTime(999);
  expect(sockets).toHaveLength(1);
  vi.advanceTimersByTime(1);
  expect(sockets).toHaveLength(2);

  sockets[1].cair();
  vi.advanceTimersByTime(1999);
  expect(sockets).toHaveLength(2);
  vi.advanceTimersByTime(1);
  expect(sockets).toHaveLength(3);

  sockets[2].abrir();
  sockets[2].cair();
  vi.advanceTimersByTime(1000);
  expect(sockets).toHaveLength(4);
});

test("a URL é pedida de novo a cada tentativa (o token pode ter mudado)", () => {
  const { criar, sockets } = fabricaDeSockets();
  const urls = ["ws://teste/a", "ws://teste/b"];
  const cliente = new TelemetriaCliente(() => urls.shift() ?? "ws://teste/c", criar);
  cliente.iniciar();
  sockets[0].cair();
  vi.advanceTimersByTime(1000);
  expect(sockets.map((s) => s.url)).toEqual(["ws://teste/a", "ws://teste/b"]);
});

test("se criar o socket falha, tenta de novo depois", () => {
  const sockets: SocketFalso[] = [];
  let chamadas = 0;
  const criar = (url: string) => {
    chamadas += 1;
    if (chamadas === 1) throw new Error("URL inválida");
    const socket = new SocketFalso(url);
    sockets.push(socket);
    return socket;
  };
  const cliente = new TelemetriaCliente(() => "ws://teste", criar);
  cliente.iniciar();
  expect(sockets).toHaveLength(0);
  vi.advanceTimersByTime(1000);
  expect(sockets).toHaveLength(1);
});

test("parar fecha o socket, cancela a reconexão e avisa parado", () => {
  const { cliente, sockets, eventos } = montar();
  cliente.iniciar();
  sockets[0].abrir();
  cliente.parar();
  expect(sockets[0].fechado).toBe(true);
  sockets[0].cair();
  vi.advanceTimersByTime(20000);
  expect(sockets).toHaveLength(1);
  expect(estados(eventos).slice(-1)).toEqual(["parado"]);
});

test("parar durante a espera cancela a reconexão agendada", () => {
  const { cliente, sockets } = montar();
  cliente.iniciar();
  sockets[0].cair();
  cliente.parar();
  vi.advanceTimersByTime(20000);
  expect(sockets).toHaveLength(1);
});

test("observer removido não é mais avisado", () => {
  const { cliente, sockets } = montar();
  const recebidos: EventoTelemetria[] = [];
  const observer = { atualizar: (e: EventoTelemetria) => recebidos.push(e) };
  cliente.adicionarObserver(observer);
  cliente.iniciar();
  cliente.removerObserver(observer);
  sockets[0].abrir();
  expect(recebidos.map((e) => (e.tipo === "conexao" ? e.estado : e.tipo))).toEqual(["conectando"]);
});

test("fechamento 1008 (token inválido ou expirado) não reconecta e avisa sessão expirada", () => {
  const { cliente, sockets, eventos } = montar();
  cliente.iniciar();
  sockets[0].abrir();
  sockets[0].cair(1008);
  vi.advanceTimersByTime(60000);
  expect(sockets).toHaveLength(1);
  expect(estados(eventos).slice(-1)).toEqual(["sessao_expirada"]);
});

test("depois de 10 tentativas seguidas sem conectar, desiste e avisa", () => {
  const { cliente, sockets, eventos } = montar();
  cliente.iniciar();
  for (let i = 0; i < 10; i++) {
    sockets[i].cair();
    vi.advanceTimersByTime(10000);
  }
  expect(sockets).toHaveLength(11);
  sockets[10].cair();
  vi.advanceTimersByTime(60000);
  expect(sockets).toHaveLength(11);
  expect(estados(eventos).slice(-1)).toEqual(["desistiu"]);
});
