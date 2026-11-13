# Semana 2 (Samuel): dispatcher com máquina de estados e sensores de alcance — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O `geraldo_dispatcher` conduz cada entrega por uma máquina de estados (eventos ao backend, `/geraldo/state`, `/geraldo/battery`, telemetria a cada 1 s) e o robô ganha os 5 sensores de alcance do contrato.

**Architecture:** Módulos pequenos e sem ROS (`states`, `ports`, `dispatcher`, `telemetry`) recebem tudo pelo construtor; só `node.py` conhece o ROS. Os sensores são um macro xacro com cinco `gpu_lidar` estreitos, cada um com uma entrada na ponte `ros_gz_bridge`.

**Tech Stack:** Python 3.12, pytest, ROS 2 Jazzy (rclpy, Nav2 `BasicNavigator`), Gazebo Harmonic, xacro, biblioteca padrão para HTTP.

**Spec:** `docs/superpowers/specs/2026-11-13-semana2-robo-design.md` (seções 3 e 4). Prioridades e emergência (seção 5) ficam para um segundo plano.

## Global Constraints

- Contrato primeiro: `POST /robot/telemetry`, `/geraldo/estop` e o significado dos estados já estão em `docs/contracts/` (commit `bf2460b`). Não criar tópico, endpoint ou campo fora dele.
- Estados (`/geraldo/state`): `IDLE`, `CARREGANDO`, `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO`, `PARADA_EMERGENCIA`.
- Eventos do robô: `LOADED`, `ARRIVED`, `UNLOCKED`, `FAILED` (`POST /robot/events`, corpo `{delivery_id, event, reason}`).
- Sensores: `/range/front_c` (0°), `/range/front_l45` (+45°), `/range/front_r45` (−45°), `/range/rear_l135` (+135°), `/range/rear_r135` (−135°), tipo `sensor_msgs/msg/LaserScan`; nenhum a 180°.
- Padrões de projeto (`docs/padroes-de-projeto.md`): uma responsabilidade por módulo, dependências injetadas pelo construtor, funções puras para transformar dados.
- Todo código novo vem com teste (falha primeiro). Commit pequeno, mensagem em português no formato `tipo: o que mudou`, terminando com a linha `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Texto de interface e mensagens de log em português; nomes de código em inglês.
- Trabalhar no worktree `.claude/worktrees/dispatcher`, branch `feat/robo-dispatcher-estados` (sensores seguem na mesma branch por enquanto). Nada na `main`.
- Simulação isolada: exportar `ROS_DOMAIN_ID=77 GZ_PARTITION=verif` em todo comando que fale com o ROS ou o Gazebo (outra sessão pode estar rodando no domínio padrão).
- Testes do dispatcher: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`. Testes do description: `source /opt/ros/jazzy/setup.bash && cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q`. Raiz: `python3 -m pytest tools robot -q`.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `geraldo_dispatcher/states.py` (novo) | `State`, tabela de transições e `StateMachine` com listeners |
| `geraldo_dispatcher/ports.py` | portas `BackendPort`, `TelemetryPort`, `Navigator` |
| `geraldo_dispatcher/api.py` | `BackendClient` (HTTP): login, tarefa, eventos, status da entrega, telemetria |
| `geraldo_dispatcher/dispatcher.py` | conduz uma entrega pela máquina de estados |
| `geraldo_dispatcher/telemetry.py` (novo) | `BatteryModel`, `build_telemetry`, `downsample`, `yaw_from_quaternion`, `TelemetryReporter` |
| `geraldo_dispatcher/node.py` | liga ao ROS: Nav2, tópicos, threads |
| `robot/scripts/fake_backend.py` | API falsa ganha eventos, status da entrega e telemetria |
| `geraldo_description/urdf/geraldo.urdf.xacro` | macro `range_sensor` e 5 instâncias |
| `geraldo_description/config/bridge.yaml` | 5 entradas `/range/*` |

---

### Task 1: Máquina de estados

**Files:**
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/states.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_states.py`

**Interfaces:**
- Produces: `State(str, Enum)` com os 7 estados; `TRANSITIONS: dict[State, set[State]]`; `StateMachine(initial=State.IDLE)` com `.state`, `.subscribe(listener: Callable[[State], None])` (não chama o listener na hora) e `.go(new: State)` (levanta `ValueError` em transição inválida, depois notifica os listeners em ordem).

- [ ] **Step 1: Escrever os testes que falham**

```python
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.states import State, StateMachine  # noqa: E402

DELIVERY = [
    State.A_CAMINHO, State.CARREGANDO, State.A_CAMINHO, State.CHEGOU,
    State.AGUARDANDO_RETIRADA, State.VOLTANDO, State.IDLE,
]


def test_state_values_match_the_openapi_contract():
    spec = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))
    assert [s.value for s in State] == spec["components"]["schemas"]["Telemetry"]["properties"]["robot_state"]["enum"]


def test_a_whole_delivery_is_a_valid_path():
    machine = StateMachine()
    for state in DELIVERY:
        machine.go(state)
    assert machine.state is State.IDLE


@pytest.mark.parametrize("stuck", [State.A_CAMINHO, State.AGUARDANDO_RETIRADA])
def test_a_failure_can_send_the_robot_back_home_from_the_trip_and_from_the_wait(stuck):
    machine = StateMachine(initial=stuck)
    machine.go(State.VOLTANDO)
    machine.go(State.IDLE)
    assert machine.state is State.IDLE


def test_invalid_transition_says_what_was_attempted():
    machine = StateMachine()
    with pytest.raises(ValueError, match="IDLE.*CHEGOU"):
        machine.go(State.CHEGOU)
    assert machine.state is State.IDLE


def test_listeners_hear_every_transition_in_order_and_not_the_subscription():
    machine, heard = StateMachine(), []
    machine.subscribe(heard.append)
    assert heard == []
    machine.go(State.A_CAMINHO)
    machine.go(State.CARREGANDO)
    assert heard == [State.A_CAMINHO, State.CARREGANDO]


def test_a_rejected_transition_does_not_notify():
    machine, heard = StateMachine(), []
    machine.subscribe(heard.append)
    with pytest.raises(ValueError):
        machine.go(State.IDLE)
    assert heard == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_states.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'geraldo_dispatcher.states'`

- [ ] **Step 3: Implementar**

```python
from collections.abc import Callable
from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    CARREGANDO = "CARREGANDO"  # na origem, até a carga ser trancada (evento LOADED)
    A_CAMINHO = "A_CAMINHO"
    CHEGOU = "CHEGOU"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"  # no destino, até o solicitante confirmar o recebimento
    VOLTANDO = "VOLTANDO"
    PARADA_EMERGENCIA = "PARADA_EMERGENCIA"  # as transições da emergência entram no plano seguinte


TRANSITIONS: dict[State, set[State]] = {
    State.IDLE: {State.A_CAMINHO},
    State.A_CAMINHO: {State.CARREGANDO, State.CHEGOU, State.VOLTANDO},
    State.CARREGANDO: {State.A_CAMINHO},
    State.CHEGOU: {State.AGUARDANDO_RETIRADA},
    State.AGUARDANDO_RETIRADA: {State.VOLTANDO},
    State.VOLTANDO: {State.IDLE},
    State.PARADA_EMERGENCIA: set(),
}


class StateMachine:
    """Guarda o estado do robô e avisa os interessados (OBSERVER) a cada transição válida."""

    def __init__(self, initial: State = State.IDLE) -> None:
        self._state = initial
        self._listeners: list[Callable[[State], None]] = []

    @property
    def state(self) -> State:
        return self._state

    def subscribe(self, listener: Callable[[State], None]) -> None:
        self._listeners.append(listener)

    def go(self, new: State) -> None:
        if new not in TRANSITIONS[self._state]:
            raise ValueError(f"Transição inválida: {self._state.value} → {new.value}.")
        self._state = new
        for listener in self._listeners:
            listener(new)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_states.py -q`
Expected: PASS (7 testes)

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/states.py robot/ros2_ws/src/geraldo_dispatcher/test/test_states.py
git commit -m "feat(dispatcher): maquina de estados do robo com listeners"
```

---

### Task 2: Portas, cliente HTTP e API falsa (eventos, status da entrega, telemetria)

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/api.py`
- Modify: `robot/scripts/fake_backend.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_api.py`

**Interfaces:**
- Produces: `BackendPort.next_task() -> dict | None`, `BackendPort.send_event(delivery_id: int, event: str, reason: str | None = None) -> bool` (`False` quando o backend responde 409; outros erros HTTP sobem), `BackendPort.delivery_status(delivery_id: int) -> str`; `TelemetryPort.send_telemetry(body: dict) -> None`; `Navigator.go_to(pose) -> bool` (igual). `BackendClient` implementa `BackendPort` e `TelemetryPort`. `FakeBackend(tasks, username, password, port, receipt_after=1, verbose=False)` com `.events: list[dict]`, `.telemetry: list[dict]`, `.reject_events: bool`; o status da entrega é `AGUARDANDO_RECEBIMENTO` nas primeiras `receipt_after` consultas e `ENTREGUE` depois.

- [ ] **Step 1: Escrever os testes que falham** (`test/test_api.py`)

```python
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.api import BackendClient  # noqa: E402
from robot.scripts.fake_backend import DEMO_TASKS, FakeBackend  # noqa: E402


@pytest.fixture
def backend():
    server = FakeBackend([dict(t) for t in DEMO_TASKS]).start()
    yield server
    server.stop()


@pytest.fixture
def client(backend):
    c = BackendClient(backend.url, "robo", "robo-local")
    c.login()
    return c


def test_send_event_posts_the_contract_body(backend, client):
    assert client.send_event(1, "FAILED", "não chegou à origem") is True
    assert backend.events == [{"delivery_id": 1, "event": "FAILED", "reason": "não chegou à origem"}]


def test_send_event_without_reason_sends_null(backend, client):
    client.send_event(1, "LOADED")
    assert backend.events[0]["reason"] is None


def test_send_event_returns_false_when_the_backend_answers_409(backend, client):
    backend.reject_events = True
    assert client.send_event(1, "UNLOCKED") is False


def test_delivery_status_waits_then_turns_delivered(backend, client):
    assert client.delivery_status(1) == "AGUARDANDO_RECEBIMENTO"
    assert client.delivery_status(1) == "ENTREGUE"


def test_send_telemetry_posts_the_body(backend, client):
    client.send_telemetry({"robot_state": "IDLE", "battery": 100})
    assert backend.telemetry == [{"robot_state": "IDLE", "battery": 100}]


def test_new_calls_log_in_again_when_the_token_expires(backend, client):
    backend.expire_token()
    assert client.delivery_status(1) == "AGUARDANDO_RECEBIMENTO"
    backend.expire_token()
    client.send_telemetry({"robot_state": "IDLE"})
    assert backend.calls.count("/auth/login") == 3
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_api.py -q`
Expected: FAIL (`AttributeError: 'BackendClient' object has no attribute 'send_event'`)

- [ ] **Step 3: Implementar `ports.py`**

```python
from abc import ABC, abstractmethod

from .waypoints import Pose


class BackendPort(ABC):  # porta: tudo o que o dispatcher precisa do backend (ISP)
    @abstractmethod
    def next_task(self) -> dict | None:
        """Próxima entrega da fila, ou None se não há nenhuma."""

    @abstractmethod
    def send_event(self, delivery_id: int, event: str, reason: str | None = None) -> bool:
        """Avisa o backend (LOADED, ARRIVED, UNLOCKED, FAILED). False se ele recusou o evento (409)."""

    @abstractmethod
    def delivery_status(self, delivery_id: int) -> str:
        """Status atual da entrega (DeliveryStatus do contrato)."""


class TelemetryPort(ABC):  # porta: só o que a telemetria precisa
    @abstractmethod
    def send_telemetry(self, body: dict) -> None:
        """Envia o corpo de Telemetry ao backend."""


class Navigator(ABC):  # porta: tudo o que o dispatcher precisa da navegação
    @abstractmethod
    def go_to(self, pose: Pose) -> bool:
        """Leva o robô até a pose. True se chegou."""
```

- [ ] **Step 4: Implementar `api.py`** (substitui o arquivo)

```python
import json
import urllib.error
import urllib.request

from .ports import BackendPort, TelemetryPort


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
        except urllib.error.HTTPError as err:
            if err.code != 401:
                raise
            self.login()
            return self._read(method, path, body)

    def _read(self, method: str, path: str, body: dict | None):
        with self._request(method, path, body) as response:
            return None if response.status == 204 else json.load(response)

    def login(self) -> None:
        try:
            with self._request("POST", "/auth/login", {"username": self.username, "password": self.password}) as response:
                self._token = json.load(response)["access_token"]
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"Login do robô falhou ({err.code}). Confira usuário e senha.") from err

    def next_task(self) -> dict | None:
        return self._json("POST", "/robot/next-task")

    def send_event(self, delivery_id: int, event: str, reason: str | None = None) -> bool:
        try:
            self._json("POST", "/robot/events", {"delivery_id": delivery_id, "event": event, "reason": reason})
            return True
        except urllib.error.HTTPError as err:
            if err.code == 409:
                return False
            raise

    def delivery_status(self, delivery_id: int) -> str:
        return self._json("GET", f"/deliveries/{delivery_id}")["status"]

    def send_telemetry(self, body: dict) -> None:
        self._json("POST", "/robot/telemetry", body)
```

- [ ] **Step 5: Implementar a API falsa** — em `robot/scripts/fake_backend.py`: (a) trocar o `import threading` por `import re` + `import threading`; (b) o docstring passa a listar também `GET /deliveries/{id}`, `POST /robot/events` e `POST /robot/telemetry`; (c) trocar o `__init__` e o `Handler` pelo bloco abaixo (o resto do arquivo, `token`, `url`, `expire_token`, `start`, `stop` e `main`, fica igual, exceto o `main` que passa `verbose=True`).

```python
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
```

Em `main()`, trocar a criação por `backend = FakeBackend(DEMO_TASKS, port=args.port, verbose=True).start()`.

- [ ] **Step 6: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS (os testes antigos do dispatcher continuam passando: `run_once` ainda não mudou).

- [ ] **Step 7: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher robot/scripts/fake_backend.py
git commit -m "feat(dispatcher): portas e cliente com eventos, status da entrega e telemetria; API falsa acompanha"
```

---

### Task 3: Dispatcher conduzido pela máquina de estados

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/dispatcher.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py` (substituir o arquivo inteiro)

**Interfaces:**
- Consumes: `StateMachine`, `State` (Task 1); `BackendPort`, `Navigator` (Task 2); `Pose`, `load_poses` de `waypoints.py`.
- Produces: `Dispatcher(backend, poses, navigator, machine=None, home="base_robo", sleep=time.sleep, poll_interval=2.0, receipt_timeout=300.0, log=print)`; atributos públicos `.machine: StateMachine` e `.delivery_id: int | None` (id da entrega em curso, `None` fora dela); `run_once() -> dict | None` devolve `None` (fila vazia), `{**task, "result": "ENTREGUE"}` ou `{**task, "result": "FALHOU", "failed_at": <waypoint>, "reason": <texto>}`.

- [ ] **Step 1: Escrever os testes que falham** — substituir `test/test_dispatcher.py` por:

```python
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.api import BackendClient  # noqa: E402
from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
from geraldo_dispatcher.ports import BackendPort, Navigator  # noqa: E402
from geraldo_dispatcher.states import State, StateMachine  # noqa: E402
from geraldo_dispatcher.waypoints import Pose, load_poses  # noqa: E402
from robot.scripts.fake_backend import DEMO_TASKS, FakeBackend  # noqa: E402

POSES = {
    "base_robo": Pose(6.5, 26.5, math.radians(270)),
    "farmacia_balcao": Pose(7, 24, math.radians(270)),
    "cons1_entrega": Pose(14.5, 4, math.radians(270)),
    "banco_sangue_retirada": Pose(17, 25, math.radians(90)),
    "cc_entrega": Pose(29, 25, math.radians(90)),
}
TASK = {"id": 5, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cc_entrega"}
WAITING = "AGUARDANDO_RECEBIMENTO"


class FakeNavigator(Navigator):  # substituto de teste do Nav2 (LSP)
    def __init__(self, fails_at=()) -> None:
        self.visited: list[Pose] = []
        self._fails_at = set(fails_at)

    def go_to(self, pose: Pose) -> bool:
        self.visited.append(pose)
        return pose not in self._fails_at


class ScriptedBackend(BackendPort):  # substituto de teste do backend: sem HTTP, com os status da entrega roteirizados
    def __init__(self, tasks, statuses=("ENTREGUE",)) -> None:
        self._tasks, self._statuses = list(tasks), list(statuses)
        self.events: list[tuple[str, str | None]] = []

    def next_task(self):
        return self._tasks.pop(0) if self._tasks else None

    def send_event(self, delivery_id, event, reason=None):
        self.events.append((event, reason))
        return True

    def delivery_status(self, delivery_id):
        return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]


def run(backend, navigator=None, poses=POSES, **kwargs):
    machine, history, sleeps = StateMachine(), [], []
    machine.subscribe(history.append)
    dispatcher = Dispatcher(backend, poses, navigator or FakeNavigator(), machine=machine, sleep=sleeps.append,
                            log=lambda *_: None, **kwargs)
    return dispatcher.run_once(), history, sleeps


@pytest.fixture
def backend():
    server = FakeBackend([dict(t) for t in DEMO_TASKS]).start()
    yield server
    server.stop()


def client_for(backend, password="robo-local"):
    return BackendClient(backend.url, "robo", password)


def test_load_poses_converts_degrees_to_radians(tmp_path):
    path = tmp_path / "w.yaml"
    path.write_text("waypoints:\n  a: {room: x, x: 1.5, y: 2.5, yaw: 90}\n", encoding="utf-8")
    pose = load_poses(path)["a"]
    assert (pose.x, pose.y) == (1.5, 2.5)
    assert pose.yaw == pytest.approx(math.pi / 2)
    z, w = pose.quaternion()
    assert z == pytest.approx(math.sin(math.pi / 4)) and w == pytest.approx(math.cos(math.pi / 4))


def test_pose_from_dict_converts_degrees_to_radians():
    pose = Pose.from_dict({"x": 1, "y": 2, "yaw": 180})
    assert (pose.x, pose.y) == (1.0, 2.0) and pose.yaw == pytest.approx(math.pi)
    assert all(isinstance(v, float) for v in (pose.x, pose.y))  # o rclpy aborta com int


def test_login_failure_has_a_clear_message(backend):
    with pytest.raises(RuntimeError, match="Login do robô falhou"):
        client_for(backend, "errada").login()


def test_next_task_returns_tasks_in_order_then_none(backend):
    client = client_for(backend)
    client.login()
    assert client.next_task()["id"] == 1
    assert client.next_task()["id"] == 2
    assert client.next_task() is None


def test_client_logs_in_again_when_the_token_expires(backend):
    client = client_for(backend)
    client.login()
    backend.expire_token()
    assert client.next_task()["id"] == 1
    assert backend.calls.count("/auth/login") == 2


def test_a_delivery_walks_the_states_and_tells_the_backend_in_order():
    scripted = ScriptedBackend([TASK])
    navigator = FakeNavigator()
    result, history, sleeps = run(scripted, navigator)
    assert history == [State.A_CAMINHO, State.CARREGANDO, State.A_CAMINHO, State.CHEGOU,
                       State.AGUARDANDO_RETIRADA, State.VOLTANDO, State.IDLE]
    assert scripted.events == [("LOADED", None), ("ARRIVED", None), ("UNLOCKED", None)]
    assert navigator.visited == [POSES["farmacia_balcao"], POSES["cc_entrega"], POSES["base_robo"]]
    assert result["id"] == 5 and result["result"] == "ENTREGUE"
    assert sleeps == []


def test_it_polls_the_delivery_until_the_requester_confirms():
    scripted = ScriptedBackend([TASK], statuses=[WAITING, WAITING, "ENTREGUE"])
    result, _, sleeps = run(scripted)
    assert result["result"] == "ENTREGUE" and sleeps == [2.0, 2.0]


def test_a_cancelled_delivery_ends_in_failure_and_goes_home():
    scripted = ScriptedBackend([TASK], statuses=["CANCELADA"])
    navigator = FakeNavigator()
    result, history, _ = run(scripted, navigator)
    assert result["result"] == "FALHOU" and result["failed_at"] == "cc_entrega" and result["reason"] == "entrega cancelada"
    assert scripted.events[-1] == ("FAILED", "entrega cancelada")
    assert history[-2:] == [State.VOLTANDO, State.IDLE] and navigator.visited[-1] == POSES["base_robo"]


def test_it_gives_up_waiting_for_the_receipt_after_the_timeout():
    scripted = ScriptedBackend([TASK], statuses=[WAITING])
    result, _, sleeps = run(scripted, receipt_timeout=6.0)
    assert sleeps == [2.0, 2.0, 2.0]
    assert result["reason"] == "recebimento não confirmado a tempo"
    assert scripted.events[-1] == ("FAILED", "recebimento não confirmado a tempo")


def test_unreachable_origin_reports_failure_and_returns_home():
    scripted = ScriptedBackend([TASK])
    navigator = FakeNavigator(fails_at=[POSES["farmacia_balcao"]])
    result, history, _ = run(scripted, navigator)
    assert result["result"] == "FALHOU" and result["failed_at"] == "farmacia_balcao"
    assert scripted.events == [("FAILED", "não chegou à origem")]
    assert history == [State.A_CAMINHO, State.VOLTANDO, State.IDLE]
    assert navigator.visited == [POSES["farmacia_balcao"], POSES["base_robo"]]


def test_unreachable_destination_reports_failure_after_loading():
    scripted = ScriptedBackend([TASK])
    result, history, _ = run(scripted, FakeNavigator(fails_at=[POSES["cc_entrega"]]))
    assert result["failed_at"] == "cc_entrega"
    assert scripted.events == [("LOADED", None), ("FAILED", "não chegou ao destino")]
    assert history == [State.A_CAMINHO, State.CARREGANDO, State.A_CAMINHO, State.VOLTANDO, State.IDLE]


def test_the_delivery_id_is_known_only_during_the_delivery():
    seen = []

    class Spy(FakeNavigator):
        def go_to(self, pose):
            seen.append(dispatcher.delivery_id)
            return super().go_to(pose)

    dispatcher = Dispatcher(ScriptedBackend([TASK]), POSES, Spy(), sleep=lambda _: None, log=lambda *_: None)
    assert dispatcher.delivery_id is None
    dispatcher.run_once()
    assert seen == [5, 5, 5] and dispatcher.delivery_id is None


def test_it_returns_none_on_an_empty_queue():
    result, history, _ = run(ScriptedBackend([]))
    assert result is None and history == []


@pytest.mark.parametrize("missing", ["farmacia_balcao", "cc_entrega", "base_robo"])
def test_a_waypoint_missing_from_the_map_is_an_error_not_a_silent_skip(missing):
    poses = {k: v for k, v in POSES.items() if k != missing}
    with pytest.raises(KeyError, match=missing):
        run(ScriptedBackend([TASK]), poses=poses)


def test_the_whole_flow_works_against_the_http_backend(backend):
    client = client_for(backend)
    client.login()
    result, _, _ = run(client)
    assert result["id"] == 1 and result["result"] == "ENTREGUE"
    assert [e["event"] for e in backend.events] == ["LOADED", "ARRIVED", "UNLOCKED"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_dispatcher.py -q`
Expected: FAIL (`TypeError: Dispatcher.__init__() got an unexpected keyword argument 'machine'`)

- [ ] **Step 3: Implementar `dispatcher.py`** (substitui o arquivo)

```python
import time

from .ports import BackendPort, Navigator
from .states import State, StateMachine
from .waypoints import Pose


class Dispatcher:
    """Conduz uma entrega: origem, carga, destino, espera do recebimento e volta à base.

    Só conhece as portas `BackendPort` e `Navigator` (DIP) e a `StateMachine`: o Nav2, o HTTP e o relógio entram
    pelo construtor. Cada passo muda o estado e avisa o backend com o evento do contrato.
    """

    def __init__(self, backend: BackendPort, poses: dict[str, Pose], navigator: Navigator,
                 machine: StateMachine | None = None, home: str = "base_robo", sleep=time.sleep,
                 poll_interval: float = 2.0, receipt_timeout: float = 300.0, log=print) -> None:
        self.backend, self.poses, self.navigator = backend, poses, navigator
        self.machine = machine or StateMachine()
        self.home, self.sleep, self.log = home, sleep, log
        self.poll_interval, self.receipt_timeout = poll_interval, receipt_timeout
        self.delivery_id: int | None = None

    def run_once(self) -> dict | None:
        task = self.backend.next_task()
        if task is None:
            return None
        for waypoint in (task["origin_waypoint"], task["dest_waypoint"], self.home):
            self._pose(waypoint)
        self.delivery_id = task["id"]
        failure = self._deliver(task)
        if failure is not None:
            self.backend.send_event(task["id"], "FAILED", failure[1])
        self.machine.go(State.VOLTANDO)
        self._go(self.home)
        self.machine.go(State.IDLE)
        self.delivery_id = None
        if failure is None:
            return {**task, "result": "ENTREGUE"}
        return {**task, "result": "FALHOU", "failed_at": failure[0], "reason": failure[1]}

    def _deliver(self, task: dict) -> tuple[str, str] | None:
        """Faz a entrega. Devolve None se deu certo, ou (waypoint onde parou, motivo)."""
        origin, dest = task["origin_waypoint"], task["dest_waypoint"]
        self.machine.go(State.A_CAMINHO)
        if not self._go(origin):
            return origin, "não chegou à origem"
        self.machine.go(State.CARREGANDO)
        self.backend.send_event(task["id"], "LOADED")
        self.machine.go(State.A_CAMINHO)
        if not self._go(dest):
            return dest, "não chegou ao destino"
        self.machine.go(State.CHEGOU)
        self.backend.send_event(task["id"], "ARRIVED")
        self.machine.go(State.AGUARDANDO_RETIRADA)
        reason = self._wait_for_receipt(task["id"])
        if reason is not None:
            return dest, reason
        self.backend.send_event(task["id"], "UNLOCKED")
        return None

    def _wait_for_receipt(self, delivery_id: int) -> str | None:
        """Espera o solicitante confirmar o recebimento. Devolve None se confirmou, ou o motivo da falha."""
        waited = 0.0
        while True:
            status = self.backend.delivery_status(delivery_id)
            if status == "ENTREGUE":
                return None
            if status in ("CANCELADA", "FALHOU"):
                return f"entrega {status.lower()}"
            if waited >= self.receipt_timeout:
                return "recebimento não confirmado a tempo"
            self.sleep(self.poll_interval)
            waited += self.poll_interval

    def _pose(self, waypoint: str) -> Pose:
        if waypoint not in self.poses:
            raise KeyError(f"Waypoint desconhecido: {waypoint}. Gere o hospital de novo (robot/hospital/gen_hospital.py).")
        return self.poses[waypoint]

    def _go(self, waypoint: str) -> bool:
        self.log(f"entrega {self.delivery_id}: indo para {waypoint}")
        reached = self.navigator.go_to(self._pose(waypoint))
        if not reached:
            self.log(f"entrega {self.delivery_id}: não chegou a {waypoint}")
        return reached
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS (todos os testes do pacote).

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat(dispatcher): entrega conduzida pela maquina de estados, com eventos e espera do recebimento"
```

---

### Task 4: Telemetria e bateria (funções puras e o reporter)

**Files:**
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/telemetry.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_telemetry.py`

**Interfaces:**
- Consumes: `State`, `StateMachine` (Task 1); `TelemetryPort` (Task 2); `Pose` (`waypoints.py`).
- Produces: `BatteryModel(level=100.0, drain_per_s=0.05, idle_drain_per_s=0.005, recharge_per_s=0.5).step(state, dt) -> float`; `build_telemetry(state, pose, battery, delivery_id, route, obstacles, now: datetime) -> dict` (corpo de `Telemetry`; `route` é lista de `(x, y)`, `obstacles` lista de `(x, y, radius)`); `downsample(points, limit=50) -> list`; `yaw_from_quaternion(z, w) -> float`; `TelemetryReporter(sink, machine, battery, pose_source, route_source, delivery_source, on_battery, clock, log=print).tick(dt)`.

- [ ] **Step 1: Escrever os testes que falham**

```python
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.ports import TelemetryPort  # noqa: E402
from geraldo_dispatcher.states import State, StateMachine  # noqa: E402
from geraldo_dispatcher.telemetry import (  # noqa: E402
    BatteryModel, TelemetryReporter, build_telemetry, downsample, yaw_from_quaternion,
)
from geraldo_dispatcher.waypoints import Pose  # noqa: E402

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def test_battery_drains_while_travelling_and_recharges_when_idle():
    battery = BatteryModel(level=50.0)
    assert battery.step(State.A_CAMINHO, 10) == pytest.approx(49.5)
    assert battery.step(State.IDLE, 10) == pytest.approx(54.5)


def test_battery_drains_slowly_while_waiting():
    assert BatteryModel(level=50.0).step(State.AGUARDANDO_RETIRADA, 10) == pytest.approx(49.95)


def test_battery_stays_between_zero_and_one_hundred():
    assert BatteryModel(level=99.9).step(State.IDLE, 10) == 100.0
    assert BatteryModel(level=0.1).step(State.VOLTANDO, 100) == 0.0


def test_build_telemetry_follows_the_contract():
    body = build_telemetry(State.A_CAMINHO, Pose(1.0, 2.0, 0.5), 87.26, 7, [(1, 2), (3, 4)], [(5, 6, 0.3)], NOW)
    spec = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))["components"]["schemas"]["Telemetry"]
    assert set(spec["required"]) <= set(body) <= set(spec["properties"])
    assert body["robot_state"] in spec["properties"]["robot_state"]["enum"]
    assert body["pose"] == {"x": 1.0, "y": 2.0, "yaw": 0.5}
    assert body["battery"] == 87.3 and body["delivery_id"] == 7
    assert body["route"] == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert body["obstacles"] == [{"x": 5, "y": 6, "radius": 0.3}]
    assert body["updated_at"] == "2026-11-13T12:00:00+00:00"


def test_downsample_keeps_the_ends_and_respects_the_limit():
    points = [(i, 0) for i in range(200)]
    small = downsample(points, limit=50)
    assert len(small) == 50 and small[0] == (0, 0) and small[-1] == (199, 0)
    assert downsample(points[:10], limit=50) == points[:10]


def test_yaw_from_quaternion_is_the_inverse_of_pose_quaternion():
    for yaw in (math.pi / 2, -math.pi / 2, 0.0, 3.0):
        z, w = Pose(0, 0, yaw).quaternion()
        assert yaw_from_quaternion(z, w) == pytest.approx(yaw)


class Sink(TelemetryPort):
    def __init__(self, fails=False):
        self.bodies, self.fails = [], fails

    def send_telemetry(self, body):
        if self.fails:
            raise OSError("sem rede")
        self.bodies.append(body)


def reporter(sink, pose=Pose(1, 2, 0.5), logs=None, levels=None):
    return TelemetryReporter(
        sink, StateMachine(), BatteryModel(level=80.0), pose_source=lambda: pose,
        route_source=lambda: [(1, 2), (3, 4)], delivery_source=lambda: 7,
        on_battery=(levels if levels is not None else []).append, clock=lambda: NOW,
        log=(logs if logs is not None else []).append,
    )


def test_tick_sends_state_pose_battery_route_and_delivery():
    sink, levels = Sink(), []
    reporter(sink, levels=levels).tick(1.0)
    body = sink.bodies[0]
    assert body["robot_state"] == "IDLE" and body["battery"] == 80.5 and body["delivery_id"] == 7
    assert levels == [80.5]


def test_tick_does_nothing_until_the_pose_is_known():
    sink = Sink()
    reporter(sink, pose=None).tick(1.0)
    assert sink.bodies == []


def test_a_telemetry_failure_is_logged_and_never_stops_the_robot():
    logs = []
    reporter(Sink(fails=True), logs=logs).tick(1.0)
    assert logs and "telemetria não enviada" in logs[0]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_telemetry.py -q`
Expected: FAIL (`ModuleNotFoundError: ... telemetry`)

- [ ] **Step 3: Implementar `telemetry.py`**

```python
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .ports import TelemetryPort
from .states import State, StateMachine
from .waypoints import Pose

TRAVELLING = {State.A_CAMINHO, State.VOLTANDO}


@dataclass
class BatteryModel:
    """Bateria virtual (a simulação não tem bateria): gasta andando, gasta pouco esperando, recarrega parada na base."""

    level: float = 100.0  # porcentagem, 0 a 100
    drain_per_s: float = 0.05
    idle_drain_per_s: float = 0.005
    recharge_per_s: float = 0.5

    def step(self, state: State, dt: float) -> float:
        if state is State.IDLE:
            self.level += self.recharge_per_s * dt
        elif state in TRAVELLING:
            self.level -= self.drain_per_s * dt
        else:
            self.level -= self.idle_drain_per_s * dt
        self.level = min(100.0, max(0.0, self.level))
        return self.level


def build_telemetry(state: State, pose: Pose, battery: float, delivery_id: int | None,
                    route: list[tuple[float, float]], obstacles: list[tuple[float, float, float]], now: datetime) -> dict:
    """Corpo de `Telemetry` do contrato (docs/contracts/openapi.yaml)."""
    return {
        "robot_state": state.value,
        "pose": {"x": pose.x, "y": pose.y, "yaw": pose.yaw},
        "battery": round(battery, 1),
        "delivery_id": delivery_id,
        "route": [{"x": x, "y": y} for x, y in route],
        "obstacles": [{"x": x, "y": y, "radius": r} for x, y, r in obstacles],
        "updated_at": now.isoformat(),
    }


def downsample(points: list, limit: int = 50) -> list:
    """No máximo `limit` pontos, espaçados por igual, sempre com o primeiro e o último."""
    if len(points) <= limit:
        return list(points)
    step = (len(points) - 1) / (limit - 1)
    return [points[round(i * step)] for i in range(limit)]


def yaw_from_quaternion(z: float, w: float) -> float:
    """Yaw (radianos) de uma rotação em torno de Z."""
    return math.atan2(2 * w * z, 1 - 2 * z * z)


class TelemetryReporter:
    """A cada `tick`: gasta a bateria, publica o nível e manda a telemetria ao backend, sem nunca derrubar o robô."""

    def __init__(self, sink: TelemetryPort, machine: StateMachine, battery: BatteryModel,
                 pose_source: Callable[[], Pose | None], route_source: Callable[[], list],
                 delivery_source: Callable[[], int | None], on_battery: Callable[[float], None],
                 clock: Callable[[], datetime], log=print) -> None:
        self.sink, self.machine, self.battery = sink, machine, battery
        self.pose_source, self.route_source, self.delivery_source = pose_source, route_source, delivery_source
        self.on_battery, self.clock, self.log = on_battery, clock, log

    def tick(self, dt: float) -> None:
        level = self.battery.step(self.machine.state, dt)
        self.on_battery(level)
        pose = self.pose_source()
        if pose is None:
            return
        body = build_telemetry(self.machine.state, pose, level, self.delivery_source(), self.route_source(), [], self.clock())
        try:
            self.sink.send_telemetry(body)
        except Exception as err:  # a telemetria é secundária: falha de rede não pode parar a entrega
            self.log(f"telemetria não enviada: {err}")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat(dispatcher): bateria virtual, corpo de telemetria do contrato e reporter"
```

---

### Task 5: Nó ROS (estado, bateria, telemetria) e verificação na simulação

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/package.xml`
- Modify: `robot/AGENTS.md`

**Interfaces:**
- Consumes: `Dispatcher`, `StateMachine`, `TelemetryReporter`, `BatteryModel`, `downsample`, `yaw_from_quaternion`, `BackendClient`.
- Produces: tópicos `/geraldo/state` (`std_msgs/String`, QoS transient_local, profundidade 1) e `/geraldo/battery` (`sensor_msgs/BatteryState`, `percentage` de 0 a 1); `POST /robot/telemetry` a cada 1 s.

- [ ] **Step 1: Declarar as dependências** — em `package.xml`, depois de `<exec_depend>geometry_msgs</exec_depend>`, acrescentar:

```xml
  <exec_depend>std_msgs</exec_depend>
  <exec_depend>sensor_msgs</exec_depend>
  <exec_depend>nav_msgs</exec_depend>
```

- [ ] **Step 2: Reescrever `node.py`** (mantém `Nav2Navigator` igual; muda os imports e o `main`)

```python
import os
import threading
import time
from datetime import datetime, timezone

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Path
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

from .api import BackendClient
from .dispatcher import Dispatcher
from .ports import Navigator
from .states import State, StateMachine
from .telemetry import BatteryModel, TelemetryReporter, downsample, yaw_from_quaternion
from .waypoints import Pose, load_poses


class Nav2Navigator(Navigator):  # ADAPTER: traduz Pose para o NavigateToPose do Nav2 (BasicNavigator)
    def __init__(self, nav: BasicNavigator, timeout: float = 300.0) -> None:
        self._nav = nav
        self._timeout = timeout

    def go_to(self, pose: Pose) -> bool:
        nav = self._nav
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = nav.get_clock().now().to_msg()
        goal.pose.position.x, goal.pose.position.y = pose.x, pose.y
        goal.pose.orientation.z, goal.pose.orientation.w = pose.quaternion()
        nav.goToPose(goal)
        start = time.monotonic()
        while not nav.isTaskComplete():
            if time.monotonic() - start > self._timeout:
                nav.cancelTask()
                break
            time.sleep(0.5)
        return nav.getResult() == TaskResult.SUCCEEDED


class GeraldoStateNode(Node):
    """Publica /geraldo/state e /geraldo/battery e guarda a última pose (AMCL) e a rota (/plan) para a telemetria."""

    def __init__(self) -> None:
        super().__init__("geraldo_state")
        self.pose: Pose | None = None
        self.route: list[tuple[float, float]] = []
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._state_pub = self.create_publisher(String, "/geraldo/state", latched)
        self._battery_pub = self.create_publisher(BatteryState, "/geraldo/battery", 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        self.create_subscription(Path, "/plan", self._on_plan, 10)

    def publish_state(self, state: State) -> None:
        self._state_pub.publish(String(data=state.value))

    def publish_battery(self, level: float) -> None:
        self._battery_pub.publish(BatteryState(percentage=level / 100.0, present=True))

    def _on_pose(self, msg: PoseWithCovarianceStamped) -> None:
        p = msg.pose.pose
        self.pose = Pose(p.position.x, p.position.y, yaw_from_quaternion(p.orientation.z, p.orientation.w))

    def _on_plan(self, msg: Path) -> None:
        self.route = downsample([(s.pose.position.x, s.pose.position.y) for s in msg.poses], 50)


def _every_second(reporter: TelemetryReporter) -> None:
    while rclpy.ok():
        time.sleep(1.0)
        reporter.tick(1.0)


def main() -> None:
    password = os.environ.get("GERALDO_ROBOT_PASSWORD") or os.environ.get("GERALDO_DEMO_PASSWORD")
    if not password:
        raise SystemExit("Defina GERALDO_ROBOT_PASSWORD (ou GERALDO_DEMO_PASSWORD) com a senha do usuário do robô.")
    api_url = os.environ.get("GERALDO_API_URL", "http://localhost:8000")

    rclpy.init()
    nav = BasicNavigator()
    nav.initial_pose_received = True  # o AMCL já tem a pose inicial; não deixe o BasicNavigator republicar (0, 0)
    nav.waitUntilNav2Active()
    waypoints_file = os.path.join(get_package_share_directory("geraldo_nav"), "config", "waypoints.yaml")
    client = BackendClient(api_url, "robo", password)
    client.login()
    machine = StateMachine()
    dispatcher = Dispatcher(client, load_poses(waypoints_file), Nav2Navigator(nav, timeout=300), machine=machine)

    state_node = GeraldoStateNode()
    machine.subscribe(state_node.publish_state)
    state_node.publish_state(machine.state)
    executor = SingleThreadedExecutor()
    executor.add_node(state_node)
    threading.Thread(target=executor.spin, daemon=True).start()

    telemetry_client = BackendClient(api_url, "robo", password)  # cliente próprio: a telemetria roda em outra thread
    telemetry_client.login()
    reporter = TelemetryReporter(
        telemetry_client, machine, BatteryModel(), pose_source=lambda: state_node.pose,
        route_source=lambda: state_node.route, delivery_source=lambda: dispatcher.delivery_id,
        on_battery=state_node.publish_battery, clock=lambda: datetime.now(timezone.utc),
    )
    threading.Thread(target=_every_second, args=(reporter,), daemon=True).start()
    try:
        while rclpy.ok():
            if dispatcher.run_once() is None:
                time.sleep(2)
    finally:
        rclpy.shutdown()
```

- [ ] **Step 3: Atualizar `robot/AGENTS.md`** — logo depois da linha `- Tópicos e estados: ...` acrescentar:

```markdown
- Dispatcher: `Dispatcher.run_once()` leva a entrega por `A_CAMINHO → CARREGANDO → A_CAMINHO → CHEGOU → AGUARDANDO_RETIRADA → VOLTANDO → IDLE` (`StateMachine` em `states.py`), avisa o backend com `LOADED`, `ARRIVED`, `UNLOCKED` ou `FAILED` e, em `AGUARDANDO_RETIRADA`, consulta `GET /deliveries/{id}` até virar `ENTREGUE`. `node.py` publica `/geraldo/state` e `/geraldo/battery` (bateria virtual) e manda `POST /robot/telemetry` a cada 1 s. Para rodar sem o backend: `python3 robot/scripts/fake_backend.py --port 8000` e `GERALDO_ROBOT_PASSWORD=robo-local ros2 run geraldo_dispatcher dispatcher`.
```

- [ ] **Step 4: Testes e build**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS
Run: `source /opt/ros/jazzy/setup.bash && cd robot/ros2_ws && colcon build --symlink-install 2>&1 | tail -3`
Expected: `Summary: 3 packages finished`

- [ ] **Step 5: Verificar na simulação** (cada comando de ROS com `export ROS_DOMAIN_ID=77 GZ_PARTITION=verif` e `source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash`)

1. Em segundo plano: `ros2 launch geraldo_description sim.launch.py headless:=true`, depois `ros2 launch geraldo_nav nav.launch.py`; esperar os nós `map_server`, `amcl`, `controller_server`, `planner_server` e `bt_navigator` ficarem `active` (`ros2 lifecycle get /<nó> | grep -q '^active'`).
2. Em segundo plano: `python3 robot/scripts/fake_backend.py --port 8000 > /tmp/fake_api.log 2>&1` e `GERALDO_ROBOT_PASSWORD=robo-local ros2 run geraldo_dispatcher dispatcher`.
3. Conferir: `ros2 topic echo --once /geraldo/state` mostra um estado válido; `ros2 topic echo --once /geraldo/battery --field percentage` mostra um número entre 0 e 1.
4. Esperar a primeira entrega (a `farmacia_balcao → cons1_entrega`, alguns minutos). Em `/tmp/fake_api.log`, nesta ordem: `POST /robot/events` (LOADED), `POST /robot/events` (ARRIVED), pelo menos um `GET /deliveries/1`, `POST /robot/events` (UNLOCKED); e, intercaladas, várias linhas `POST /robot/telemetry`. O log só mostra a rota, não o corpo; a ordem LOADED, ARRIVED, UNLOCKED já é garantida pelo teste do dispatcher.
5. Parar tudo (só os processos deste domínio).
Expected: o dispatcher termina a entrega 1 e começa a 2 sem erro; nenhuma exceção no terminal do dispatcher.

- [ ] **Step 6: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher robot/AGENTS.md
git commit -m "feat(dispatcher): no ROS publica estado, bateria e telemetria a cada 1 s"
```

---

### Task 6: Cinco sensores de alcance no URDF e na ponte

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`
- Modify: `robot/ros2_ws/src/geraldo_description/config/bridge.yaml`
- Modify: `robot/ros2_ws/src/geraldo_description/test/test_urdf.py`
- Modify: `robot/ros2_ws/src/geraldo_description/test/test_launch_files.py`

**Interfaces:**
- Produces: links `range_<nome>_link` e juntas `range_<nome>_joint` (fixas, filhas de `base_link`, z = 0,15) para `<nome>` em `front_c`, `front_l45`, `front_r45`, `rear_l135`, `rear_r135`; sensores `gpu_lidar` com tópico Gazebo `range/<nome>` (5 amostras em ±0,087 rad, alcance 0,05 a 2,0 m); entradas na ponte com `ros_topic_name: /range/<nome>`, tipo `sensor_msgs/msg/LaserScan`, `GZ_TO_ROS`.

Posições (x, y, yaw em rad): `front_c` (0,36, 0, 0); `front_l45` (0,33, 0,26, 0,7854); `front_r45` (0,33, −0,26, −0,7854); `rear_l135` (−0,33, 0,26, 2,3562); `rear_r135` (−0,33, −0,26, −2,3562). Ficam um pouco fora da carcaça (0,70 × 0,50 m) para o raio não nascer dentro dela.

- [ ] **Step 1: Escrever os testes que falham**

Em `test_urdf.py`: no `test_links_and_joints_exist`, trocar os dois conjuntos por

```python
RANGE = ("front_c", "front_l45", "front_r45", "rear_l135", "rear_r135")


def test_links_and_joints_exist(robot):
    assert {l.get("name") for l in robot.findall("link")} == {
        "base_link", "wheel_left_link", "wheel_right_link", "caster_swivel_link", "caster_wheel_link", "lidar_link",
        *(f"range_{n}_link" for n in RANGE),
    }
    assert set(joints(robot)) == {
        "wheel_left_joint", "wheel_right_joint", "caster_swivel_joint", "caster_wheel_joint", "lidar_joint",
        *(f"range_{n}_joint" for n in RANGE),
    }
```

e acrescentar no fim do arquivo:

```python
RANGE_LAYOUT = {  # nome: (x, y, yaw em radianos); nenhum sensor a 180 graus (a traseira fica livre)
    "front_c": (0.36, 0.0, 0.0),
    "front_l45": (0.33, 0.26, 0.7854),
    "front_r45": (0.33, -0.26, -0.7854),
    "rear_l135": (-0.33, 0.26, 2.3562),
    "rear_r135": (-0.33, -0.26, -2.3562),
}


@pytest.mark.parametrize("name", RANGE_LAYOUT)
def test_range_sensor_sits_on_the_chassis_pointing_where_the_contract_says(robot, name):
    joint = joints(robot)[f"range_{name}_joint"]
    x, y, yaw = RANGE_LAYOUT[name]
    assert joint.get("type") == "fixed" and joint.find("parent").get("link") == "base_link"
    assert xyz(joint) == pytest.approx([x, y, 0.15])
    assert float(joint.find("origin").get("rpy").split()[2]) == pytest.approx(yaw)


@pytest.mark.parametrize("name", RANGE_LAYOUT)
def test_range_sensor_publishes_a_narrow_short_range_scan(robot, name):
    sensor = next(s for g in robot.findall("gazebo") if g.get("reference") == f"range_{name}_link" for s in g.findall("sensor"))
    assert sensor.get("type") == "gpu_lidar"
    assert sensor.find("topic").text == f"range/{name}"
    assert sensor.find("gz_frame_id").text == f"range_{name}_link"
    assert int(sensor.find("lidar/scan/horizontal/samples").text) == 5
    assert float(sensor.find("lidar/range/max").text) == pytest.approx(2.0)
```

Em `test_launch_files.py`, no `test_bridge_has_the_contract_topics`, trocar o conjunto esperado e acrescentar a checagem:

```python
    assert set(by_topic) == {"/clock", "/cmd_vel", "/odom", "/tf", "/scan",
                             "/range/front_c", "/range/front_l45", "/range/front_r45",
                             "/range/rear_l135", "/range/rear_r135"}
    for topic in set(by_topic) - {"/clock", "/cmd_vel", "/odom", "/tf"}:
        assert by_topic[topic]["ros_type_name"] == "sensor_msgs/msg/LaserScan"
        assert by_topic[topic]["gz_type_name"] == "gz.msgs.LaserScan"
        assert by_topic[topic]["direction"] == "GZ_TO_ROS"
```

(as três últimas asserções do teste original sobre `/cmd_vel`, `/scan` e `/tf` continuam).

- [ ] **Step 2: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q`
Expected: FAIL (links e entradas de ponte ausentes)

- [ ] **Step 3: Implementar o URDF** — em `geraldo.urdf.xacro`, antes do bloco `<gazebo>` do plugin `gz-sim-diff-drive-system`, inserir:

```xml
  <!-- Sensores de alcance (contrato): 5 feixes estreitos de até 2 m, um pouco fora da carcaça; nenhum a 180 graus -->
  <xacro:macro name="range_sensor" params="name x y yaw">
    <link name="range_${name}_link">
      <inertial>
        <mass value="0.01"/>
        <inertia ixx="0.000001" ixy="0" ixz="0" iyy="0.000001" iyz="0" izz="0.000001"/>
      </inertial>
    </link>
    <joint name="range_${name}_joint" type="fixed">
      <parent link="base_link"/>
      <child link="range_${name}_link"/>
      <origin xyz="${x} ${y} 0.15" rpy="0 0 ${yaw}"/>
    </joint>
    <gazebo reference="range_${name}_link">
      <sensor name="range_${name}" type="gpu_lidar">
        <pose>0 0 0 0 0 0</pose>
        <topic>range/${name}</topic>
        <gz_frame_id>range_${name}_link</gz_frame_id>
        <update_rate>10</update_rate>
        <always_on>true</always_on>
        <visualize>false</visualize>
        <lidar>
          <scan>
            <horizontal>
              <samples>5</samples>
              <resolution>1</resolution>
              <min_angle>-0.087</min_angle>
              <max_angle>0.087</max_angle>
            </horizontal>
          </scan>
          <range>
            <min>0.05</min>
            <max>2.0</max>
            <resolution>0.01</resolution>
          </range>
        </lidar>
      </sensor>
    </gazebo>
  </xacro:macro>
  <xacro:range_sensor name="front_c" x="0.36" y="0.0" yaw="0.0"/>
  <xacro:range_sensor name="front_l45" x="0.33" y="0.26" yaw="0.7854"/>
  <xacro:range_sensor name="front_r45" x="0.33" y="-0.26" yaw="-0.7854"/>
  <xacro:range_sensor name="rear_l135" x="-0.33" y="0.26" yaw="2.3562"/>
  <xacro:range_sensor name="rear_r135" x="-0.33" y="-0.26" yaw="-2.3562"/>

```

Também atualizar o comentário do LiDAR ("A traseira é coberta pelos sensores de alcance a 135 graus (semana 2).") para "A traseira é coberta pelos sensores de alcance a 135 graus (`range_rear_*`)."

- [ ] **Step 4: Implementar a ponte** — acrescentar ao fim de `config/bridge.yaml`, um bloco por sensor (trocar `<nome>`):

```yaml

- ros_topic_name: /range/<nome>
  gz_topic_name: /range/<nome>
  ros_type_name: sensor_msgs/msg/LaserScan
  gz_type_name: gz.msgs.LaserScan
  direction: GZ_TO_ROS
```

para `front_c`, `front_l45`, `front_r45`, `rear_l135` e `rear_r135`.

- [ ] **Step 5: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add robot/ros2_ws/src/geraldo_description
git commit -m "feat(description): cinco sensores de alcance (0, +-45 e +-135 graus) no URDF e na ponte"
```

---

### Task 7: Verificar os sensores na simulação

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_description/test/smoke_sim.sh`
- Modify: `robot/AGENTS.md`

- [ ] **Step 1: Estender o smoke** — em `smoke_sim.sh`, depois da linha `timeout 30 ros2 topic echo --once /scan --field ranges > /dev/null`, acrescentar:

```bash
for sensor in front_c front_l45 front_r45 rear_l135 rear_r135; do
  timeout 30 ros2 topic echo --once "/range/$sensor" --field ranges > /dev/null
done
```

- [ ] **Step 2: Build e smoke**

Run: `source /opt/ros/jazzy/setup.bash && cd robot/ros2_ws && colcon build --symlink-install 2>&1 | tail -2 && source install/setup.bash && export ROS_DOMAIN_ID=77 GZ_PARTITION=verif && bash src/geraldo_description/test/smoke_sim.sh`
Expected: termina em `SMOKE OK` (a sim sobe, `/scan` e os 5 `/range/*` respondem, o robô anda).

- [ ] **Step 3: Conferir que os feixes enxergam algo** — com a sim no ar (sem Nav2), mandar o robô para perto de uma parede e ler os alcances:

Run: `ros2 topic echo --once /range/front_c --field ranges` e `ros2 topic echo --once /range/rear_l135 --field ranges`
Expected: 5 valores cada; no ponto de partida (6,5; 26,5, de costas para a parede sul da farmácia, a 1,5 m) os valores são `inf` ou números de 0,05 a 2,0, nunca `nan` nem lista vazia. Anotar os valores no commit.

- [ ] **Step 4: Documentar** — em `robot/AGENTS.md`, depois do bullet do dispatcher, acrescentar:

```markdown
- Sensores de alcance: `range_front_c`, `range_front_l45`, `range_front_r45`, `range_rear_l135` e `range_rear_r135` (macro `range_sensor` no URDF; 5 feixes de ±5° e até 2 m) saem em `/range/<nome>` (`LaserScan`, ponte em `config/bridge.yaml`). Nenhum a 180°. O Nav2 ainda não usa esses tópicos.
```

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_description/test/smoke_sim.sh robot/AGENTS.md
git commit -m "test(description): smoke confere os 5 sensores de alcance; AGENTS documenta"
```

---

### Task 8: Suíte final e varredura dos 10 pontos com os sensores

**Files:** nenhum arquivo novo (só evidências).

- [ ] **Step 1: Suíte da raiz e dos pacotes**

Run: `python3 -m pytest tools robot -q`
Expected: PASS
Run: `source /opt/ros/jazzy/setup.bash && for p in geraldo_dispatcher geraldo_description; do (cd robot/ros2_ws/src/$p && python3 -m pytest test -q); done`
Expected: PASS nos dois.

- [ ] **Step 2: Varredura dos 10 pontos com os 5 sensores extras** (risco da spec: carga da simulação) — com `ROS_DOMAIN_ID=77 GZ_PARTITION=verif`: sim headless, Nav2 com os 5 nós `active` (`grep -q '^active'`), depois `python3 robot/scripts/nav_goal_sweep.py` (~10 min).
Expected: `TODOS OS PONTOS OK`. Anotar o tempo por ponto e comparar com a rodada anterior (5 s a 122 s por ponto). Se o Nav2 cair por heartbeat do `collision_monitor`, medir a carga (`uptime`) e reduzir `update_rate` dos `range_*` de 10 para 5.

- [ ] **Step 3: Conferir o working tree e a branch**

Run: `git status --short && git log --oneline -8`
Expected: árvore limpa; commits das Tasks 1 a 7 sobre `2c7c78e`.

- [ ] **Step 4: Resumir** — escrever no resultado final o que passou, o que não foi verificado e os avisos pendentes: Erik (implementar `POST /robot/telemetry`; confirmar se aceita `UNLOCKED` depois de `ENTREGUE`) e Pedro (campo `obstacles` da telemetria). Não abrir PR sem pedido do Samuel.
