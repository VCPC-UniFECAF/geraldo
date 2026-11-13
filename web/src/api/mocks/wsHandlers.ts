import { ws } from "msw";
import { roboSimulado } from "./robo";

// Só o modo demo (`npm run dev:demo`) usa este handler: os testes trocam o socket por um falso (src/test/SocketFalso.ts).
const telemetria = ws.link("ws://localhost:8000/ws/telemetry");

export const wsHandlers = [
  telemetria.addEventListener("connection", ({ client }) => {
    client.send(JSON.stringify(roboSimulado.atual()));
    const timer = setInterval(() => client.send(JSON.stringify(roboSimulado.avancar())), 1000);
    client.addEventListener("close", () => clearInterval(timer));
  }),
];
