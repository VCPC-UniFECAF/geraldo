import json
import urllib.error
import urllib.request

from .ports import BackendError, BackendPort, TelemetryPort


class BackendClient(BackendPort, TelemetryPort):  # ADAPTER: traduz a API HTTP do backend para as portas do robô
    """Cliente mínimo do backend (só biblioteca padrão): login, tarefa, eventos, status da entrega e telemetria."""

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.username, self.password, self.timeout = username, password, timeout
        self._token: str | None = None

    def _request(self, method: str, path: str, body: dict | None = None):
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if body is not None:
            data = json.dumps(body).encode()
        else:
            data = b"" if method == "POST" else None
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        return urllib.request.urlopen(request, timeout=self.timeout)

    def _json(self, method: str, path: str, body: dict | None = None):
        """Chama o backend e devolve o JSON da resposta (None se vier 204). Se o token expirou, entra de novo uma vez."""
        try:
            return self._read(method, path, body)
        except BackendError as err:
            if err.status != 401:
                raise
            self.login()
            return self._read(method, path, body)

    def _read(self, method: str, path: str, body: dict | None):
        try:
            with self._request(method, path, body) as response:
                return None if response.status == 204 else json.load(response)
        except urllib.error.HTTPError as err:
            raise BackendError(f"O backend respondeu {err.code} em {method} {path}.", err.code) from err
        except (urllib.error.URLError, OSError) as err:  # HTTPError já foi tratado acima (é um URLError)
            raise BackendError(self._down(err)) from err

    def _down(self, err: Exception) -> str:
        return f"Backend fora do ar ou sem resposta ({self.base_url}): {err}. Confira se ele está rodando."

    def login(self) -> None:
        try:
            with self._request("POST", "/auth/login", {"username": self.username, "password": self.password}) as response:
                self._token = json.load(response)["access_token"]
        except urllib.error.HTTPError as err:
            raise BackendError(f"Login do robô falhou ({err.code}). Confira usuário e senha.", err.code) from err
        except (urllib.error.URLError, OSError) as err:
            raise BackendError(self._down(err)) from err

    def next_task(self) -> dict | None:
        return self._json("POST", "/robot/next-task")

    def send_event(self, delivery_id: int, event: str, reason: str | None = None) -> bool:
        try:
            self._json("POST", "/robot/events", {"delivery_id": delivery_id, "event": event, "reason": reason})
            return True
        except BackendError as err:
            if err.status == 409:
                return False
            raise

    def delivery_status(self, delivery_id: int) -> str:
        return self._json("GET", f"/deliveries/{delivery_id}")["status"]

    def send_telemetry(self, body: dict) -> None:
        self._json("POST", "/robot/telemetry", body)
