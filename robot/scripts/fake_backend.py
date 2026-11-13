#!/usr/bin/env python3
"""API falsa do robô para desenvolver o dispatcher sem o backend. Segue docs/contracts/openapi.yaml
(POST /auth/login, POST /robot/next-task, POST /robot/events, POST /robot/telemetry e GET /deliveries/{id}).

Uso: python robot/scripts/fake_backend.py --port 8000     (usuário `robo`, senha `robo-local`)
"""
import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEMO_TASKS = [
    {"id": 1, "origin_id": "farmacia", "dest_id": "consultorio1", "items": [{"item_id": "dipirona-500mg", "quantity": 5}],
     "priority": "media", "status": "EM_ROTA", "requested_by": 1, "created_at": "2026-11-09T13:20:00Z",
     "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega"},
    {"id": 2, "origin_id": "banco_sangue", "dest_id": "centro_cirurgico", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}],
     "priority": "critica", "status": "EM_ROTA", "requested_by": 1, "created_at": "2026-11-09T13:25:00Z",
     "origin_waypoint": "banco_sangue_retirada", "dest_waypoint": "cc_entrega"},
]


class FakeBackend:
    def __init__(self, tasks=None, username="robo", password="robo-local", port=0, receipt_after=1, verbose=False) -> None:
        self.tasks = list(tasks or [])
        self.username, self.password = username, password
        self.token_number = 1
        self.calls: list[str] = []
        self.events: list[dict] = []
        self.telemetry: list[dict] = []
        self.polls: dict[int, int] = {}
        self.receipt_after = receipt_after  # quantas consultas a entrega fica em AGUARDANDO_RECEBIMENTO
        self.reject_events = False          # responde 409 a todo evento
        self.delivery_status_code = 200     # outro valor: a consulta da entrega responde esse código
        self.verbose = verbose
        backend = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                if backend.verbose:
                    print("API falsa:", fmt % args, flush=True)

            def _send(self, code, body=None):
                payload = json.dumps(body).encode() if body is not None else b""
                self.send_response(code)
                if body is not None:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _unauthorized(self) -> bool:
                if self.headers.get("Authorization") == f"Bearer {backend.token}":
                    return False
                self._send(401, {"detail": "Sessão inválida ou expirada. Entre de novo."})
                return True

            def do_GET(self):
                backend.calls.append(self.path)
                if self._unauthorized():
                    return
                if backend.delivery_status_code != 200:
                    return self._send(backend.delivery_status_code, {"detail": "Entrega não encontrada."})
                match = re.fullmatch(r"/deliveries/(\d+)", self.path)
                if not match:
                    return self._send(404, {"detail": "Não encontrado."})
                delivery_id = int(match.group(1))
                backend.polls[delivery_id] = backend.polls.get(delivery_id, 0) + 1
                done = backend.polls[delivery_id] > backend.receipt_after
                return self._send(200, {"id": delivery_id, "status": "ENTREGUE" if done else "AGUARDANDO_RECEBIMENTO"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                backend.calls.append(self.path)
                if self.path == "/auth/login":
                    body = json.loads(raw)
                    if body.get("username") == backend.username and body.get("password") == backend.password:
                        return self._send(200, {"access_token": backend.token, "token_type": "bearer"})
                    return self._send(401, {"detail": "Usuário ou senha incorretos. Tente de novo."})
                if self._unauthorized():
                    return
                if self.path == "/robot/next-task":
                    return self._send(200, backend.tasks.pop(0)) if backend.tasks else self._send(204)
                if self.path == "/robot/events":
                    if backend.reject_events:
                        return self._send(409, {"detail": "Evento não cabe no estado atual da entrega."})
                    body = json.loads(raw)
                    backend.events.append(body)
                    return self._send(200, {"id": body["delivery_id"], "status": "EM_ROTA"})
                if self.path == "/robot/telemetry":
                    backend.telemetry.append(json.loads(raw))
                    return self._send(204)
                return self._send(404, {"detail": "Não encontrado."})

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def token(self) -> str:
        return f"fake-token-{self.token_number}"

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def expire_token(self) -> None:
        self.token_number += 1

    def start(self) -> "FakeBackend":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    backend = FakeBackend(DEMO_TASKS, port=args.port, verbose=True).start()
    print(f"API falsa em {backend.url} (usuário robo, senha robo-local). Ctrl+C para sair.")
    threading.Event().wait()


if __name__ == "__main__":
    main()
