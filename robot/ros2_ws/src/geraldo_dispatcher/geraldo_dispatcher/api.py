import json
import urllib.error
import urllib.request

from .ports import BackendPort


class BackendClient(BackendPort):  # ADAPTER: traduz a API HTTP do backend para a porta que o dispatcher usa
    """Cliente mínimo do backend (só biblioteca padrão): login do robô e próxima tarefa."""

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.username, self.password, self.timeout = username, password, timeout
        self._token: str | None = None

    def _post(self, path: str, body: dict | None = None):
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        data = json.dumps(body).encode() if body is not None else b""
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method="POST")
        return urllib.request.urlopen(request, timeout=self.timeout)

    def login(self) -> None:
        try:
            with self._post("/auth/login", {"username": self.username, "password": self.password}) as response:
                self._token = json.load(response)["access_token"]
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"Login do robô falhou ({err.code}). Confira usuário e senha.") from err

    def next_task(self) -> dict | None:
        try:
            return self._read_task()
        except urllib.error.HTTPError as err:
            if err.code != 401:
                raise
            self.login()  # o token expirou: entra de novo uma vez
            return self._read_task()

    def _read_task(self) -> dict | None:
        with self._post("/robot/next-task") as response:
            return None if response.status == 204 else json.load(response)
