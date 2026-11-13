# Integração do robô com backend, web e robô de mentira — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar as lacunas entre o `geraldo_dispatcher` e as frentes do Erik, do Vieira e do Pedro: contrato de leitura da entrega pelo robô, tolerância a falhas do backend, consistência entre seeds e waypoints, exemplos gerados do código e o protocolo escrito.

**Architecture:** `BackendError` nasce na porta (`ports.py`) e o `BackendClient` traduz todo erro de rede e HTTP para ele; o `Dispatcher` reenvia eventos e tolera falhas de consulta; o nó espera o backend voltar. Os exemplos saem de `contract_examples.py`, que roda o próprio `build_telemetry` e o próprio `Dispatcher`, e são validados contra o OpenAPI por `openapi_check.py`.

**Tech Stack:** Python 3.12, pytest, PyYAML (já usado), biblioteca padrão para HTTP.

**Spec:** `docs/superpowers/specs/2026-11-13-integracao-robo-design.md`

## Global Constraints

- Contrato primeiro: a única mudança de contrato deste plano é a regra de leitura do `robo` em `GET /deliveries/{id}` (Task 1), em commit isolado. Nenhum endpoint, tópico ou campo novo além dos que já estão em `docs/contracts/`.
- Estados: `IDLE`, `CARREGANDO`, `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO`, `PARADA_EMERGENCIA`. Eventos: `LOADED`, `ARRIVED`, `UNLOCKED`, `FAILED`.
- Nenhuma dependência nova (sem `jsonschema`, `httpx` ou `requests`).
- Padrões de projeto (`docs/padroes-de-projeto.md`): uma responsabilidade por módulo, dependências pelo construtor, relógio e `sleep` injetados.
- Todo código novo vem com teste (falha primeiro). Commit pequeno em português (`tipo: o que mudou`), terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Mensagens de erro e de log em português, dizendo o que houve e o que fazer.
- Branch `feat/robo-dispatcher-estados`, worktree `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher` (usar caminhos absolutos do worktree).
- Testes do dispatcher: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`. Raiz: `python3 -m pytest tools robot -q`.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `docs/contracts/openapi.yaml` | regra de leitura do `robo` em `GET /deliveries/{id}` |
| `geraldo_dispatcher/ports.py` | `BackendError(RuntimeError)` com `.status` |
| `geraldo_dispatcher/api.py` | traduz erros de rede e HTTP para `BackendError` |
| `geraldo_dispatcher/dispatcher.py` | `_notify` com reenvio; espera do recebimento tolera erro de consulta |
| `geraldo_dispatcher/node.py` | login e laço principal esperam o backend voltar |
| `robot/scripts/fake_backend.py` | `delivery_status_code` para simular erro na consulta |
| `robot/hospital/tests/test_seeds_consistency.py` (novo) | seeds do backend x waypoints do robô |
| `robot/scripts/openapi_check.py` (novo) | `validate(value, schema, spec)` (subconjunto do OpenAPI) |
| `robot/scripts/contract_examples.py` (novo) | gera os exemplos de telemetria e de eventos |
| `docs/contracts/examples/robot-telemetry.json`, `robot-events.json` (novos, gerados) | fixtures para Vieira e Pedro |
| `docs/contracts/robot-protocol.md` (novo) | protocolo e avisos |

---

### Task 1: Contrato — o robô pode consultar a entrega

**Files:**
- Modify: `docs/contracts/openapi.yaml` (`/deliveries/{id}`, `get`)
- Test: `tools/tests/test_contracts.py`

**Interfaces:**
- Produces: a descrição de `GET /deliveries/{id}` cita o papel `robo`.

- [ ] **Step 1: Escrever o teste que falha** — acrescentar ao fim de `tools/tests/test_contracts.py`:

```python
def test_the_robot_may_read_a_delivery_to_wait_for_the_receipt():
    operation = load()["paths"]["/deliveries/{id}"]["get"]
    assert "robo" in operation["description"] and "somente leitura" in operation["description"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher && python3 -m pytest tools/tests/test_contracts.py -q`
Expected: FAIL (`KeyError: 'description'`)

- [ ] **Step 3: Implementar** — em `openapi.yaml`, trocar

```yaml
      summary: Consulta uma entrega
      parameters:
```

por

```yaml
      summary: Consulta uma entrega
      description: >
        O solicitante vê as suas; admin e farmacêutico veem todas. O papel robo também pode consultar
        qualquer entrega, somente leitura: o dispatcher espera o status virar ENTREGUE (ver docs/contracts/robot-protocol.md).
      parameters:
```

(a troca vale só para o `get` de `/deliveries/{id}`; o trecho `summary: Consulta uma entrega` aparece uma vez).

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tools -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/contracts/openapi.yaml tools/tests/test_contracts.py
git commit -m "docs(contratos): o papel robo pode consultar GET /deliveries/{id}"
```

---

### Task 2: `BackendError` e o cliente HTTP

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/api.py`
- Modify: `robot/scripts/fake_backend.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_api.py`

**Interfaces:**
- Produces: `BackendError(message: str, status: int | None = None)` (herda de `RuntimeError`; `.status` é o código HTTP ou `None` quando o backend não respondeu). `BackendClient` levanta só `BackendError`: login com senha errada (`status` 401, mensagem começa com `Login do robô falhou`), qualquer HTTP fora de 2xx depois do relogin em 401, e backend fora do ar (mensagem começa com `Backend fora do ar`). `send_event` continua devolvendo `False` no 409. `FakeBackend.delivery_status_code: int = 200` (se diferente de 200, `GET /deliveries/{id}` responde esse código).

- [ ] **Step 1: Escrever os testes que falham** — em `test_api.py`: acrescentar `from geraldo_dispatcher.ports import BackendError  # noqa: E402` entre os imports e, no fim do arquivo:

```python
def test_an_http_error_becomes_a_backend_error_with_the_status(backend, client):
    backend.delivery_status_code = 404
    with pytest.raises(BackendError, match="404") as caught:
        client.delivery_status(1)
    assert caught.value.status == 404


def test_a_backend_that_is_down_becomes_a_backend_error_without_status():
    down = BackendClient("http://127.0.0.1:9", "robo", "robo-local", timeout=1.0)
    with pytest.raises(BackendError, match="Backend fora do ar") as caught:
        down.next_task()
    assert caught.value.status is None


def test_login_against_a_backend_that_is_down_says_so():
    with pytest.raises(BackendError, match="Backend fora do ar"):
        BackendClient("http://127.0.0.1:9", "robo", "robo-local", timeout=1.0).login()


def test_a_wrong_password_is_a_backend_error_with_status_401(backend):
    with pytest.raises(BackendError, match="Login do robô falhou") as caught:
        BackendClient(backend.url, "robo", "errada").login()
    assert caught.value.status == 401 and isinstance(caught.value, RuntimeError)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher/robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_api.py -q`
Expected: FAIL (`ImportError: cannot import name 'BackendError'`)

- [ ] **Step 3: Implementar** — em `ports.py`, depois dos imports e antes de `BackendPort`:

```python
class BackendError(RuntimeError):
    """O backend recusou o pedido (status HTTP em `.status`) ou não respondeu (`.status` é None)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
```

Em `api.py`, trocar o import `from .ports import BackendPort, TelemetryPort` por `from .ports import BackendError, BackendPort, TelemetryPort` e substituir `_json`, `_read`, `login` e `send_event` por:

```python
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

    def send_event(self, delivery_id: int, event: str, reason: str | None = None) -> bool:
        try:
            self._json("POST", "/robot/events", {"delivery_id": delivery_id, "event": event, "reason": reason})
            return True
        except BackendError as err:
            if err.status == 409:
                return False
            raise
```

(`next_task`, `delivery_status` e `send_telemetry` ficam como estão.) Em `fake_backend.py`: no `__init__`, depois de `self.reject_events = False`, acrescentar `self.delivery_status_code = 200       # outro valor: a consulta da entrega responde esse código`; e no `do_GET`, logo depois do `if self._unauthorized(): return`, acrescentar:

```python
                if backend.delivery_status_code != 200:
                    return self._send(backend.delivery_status_code, {"detail": "Entrega não encontrada."})
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher/robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS (os testes antigos de login, 409 e relogin continuam passando)

- [ ] **Step 5: Commit**

```bash
git add robot
git commit -m "feat(dispatcher): o cliente do backend so levanta BackendError, com o status HTTP"
```

---

### Task 3: O dispatcher e o nó sobrevivem a falhas do backend

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/dispatcher.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py`

**Interfaces:**
- Consumes: `BackendError` (Task 2).
- Produces: `Dispatcher(..., event_retries: int = 3, retry_wait: float = 1.0, ...)`. Eventos: até `event_retries` tentativas, `retry_wait` s entre elas; esgotadas, loga e segue. Consulta do recebimento: `BackendError` conta como "ainda não"; no timeout o motivo vira `recebimento não confirmado a tempo (<mensagem do último erro>)` quando houve erro.

- [ ] **Step 1: Escrever os testes que falham** — em `test_dispatcher.py`: trocar `from geraldo_dispatcher.ports import BackendPort, NavigationTuner, Navigator  # noqa: E402` por `from geraldo_dispatcher.ports import BackendError, BackendPort, NavigationTuner, Navigator  # noqa: E402` e acrescentar no fim:

```python
class FlakyEvents(ScriptedBackend):  # send_event falha `fails` vezes
    def __init__(self, tasks, fails) -> None:
        super().__init__(tasks)
        self.fails = fails

    def send_event(self, delivery_id, event, reason=None):
        if self.fails > 0:
            self.fails -= 1
            raise BackendError("O backend respondeu 500 em POST /robot/events.", 500)
        return super().send_event(delivery_id, event, reason)


class FlakyStatus(ScriptedBackend):  # delivery_status falha `errors` vezes
    def __init__(self, tasks, errors) -> None:
        super().__init__(tasks)
        self.errors = errors

    def delivery_status(self, delivery_id):
        if self.errors > 0:
            self.errors -= 1
            raise BackendError(f"O backend respondeu 404 em GET /deliveries/{delivery_id}.", 404)
        return "ENTREGUE"


def test_an_event_is_retried_while_the_backend_is_down_and_the_delivery_goes_on():
    flaky = FlakyEvents([TASK], fails=2)
    result, _, sleeps = run(flaky)
    assert result["result"] == "ENTREGUE"
    assert [event for event, _ in flaky.events] == ["LOADED", "ARRIVED", "UNLOCKED"]
    assert sleeps == [1.0, 1.0]


def test_an_event_that_never_gets_through_is_dropped_without_stopping_the_robot():
    flaky = FlakyEvents([TASK], fails=99)
    result, history, sleeps = run(flaky)
    assert result["result"] == "ENTREGUE" and flaky.events == [] and history[-1] is State.IDLE
    assert sleeps == [1.0] * 6  # 3 eventos x 2 esperas entre as 3 tentativas


def test_the_receipt_wait_survives_errors_while_polling():
    result, _, sleeps = run(FlakyStatus([TASK], errors=2))
    assert result["result"] == "ENTREGUE" and sleeps == [2.0, 2.0]


def test_a_status_that_never_answers_ends_unconfirmed_and_says_why():
    result, _, _ = run(FlakyStatus([TASK], errors=999), receipt_timeout=4.0)
    assert result["result"] == "FALHOU"
    assert result["reason"].startswith("recebimento não confirmado a tempo") and "404" in result["reason"]


def test_a_backend_that_hides_the_delivery_from_the_robot_ends_unconfirmed_instead_of_crashing(backend):
    backend.delivery_status_code = 404  # o que o plano da semana 1 do Erik faria com o papel robo
    client = client_for(backend)
    client.login()
    result, _, _ = run(client, receipt_timeout=4.0)
    assert result["result"] == "FALHOU" and "404" in result["reason"]
    assert [e["event"] for e in backend.events] == ["LOADED", "ARRIVED", "FAILED"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher/robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_dispatcher.py -q`
Expected: FAIL (`BackendError` sobe de dentro do `run_once`)

- [ ] **Step 3: Implementar** — em `dispatcher.py`: (a) trocar o import por `from .ports import BackendError, BackendPort, NavigationTuner, Navigator`; (b) no `__init__`, acrescentar ao fim da assinatura, antes de `log=print`, `event_retries: int = 3, retry_wait: float = 1.0,` e, no corpo, `self.event_retries, self.retry_wait = event_retries, retry_wait`; (c) trocar toda chamada `self.backend.send_event(` por `self._notify(` (são 4: `FAILED`, `LOADED`, `ARRIVED`, `UNLOCKED`; os argumentos não mudam); (d) acrescentar o método

```python
    def _notify(self, delivery_id: int, event: str, reason: str | None = None) -> None:
        """Avisa o backend. Fora do ar: tenta de novo algumas vezes e segue com a entrega (a carga está com o robô)."""
        for attempt in range(1, self.event_retries + 1):
            try:
                if not self.backend.send_event(delivery_id, event, reason):
                    self.log(f"entrega {delivery_id}: o backend recusou o evento {event}")
                return
            except BackendError as err:
                self.log(f"entrega {delivery_id}: evento {event} não enviado ({err}) [{attempt}/{self.event_retries}]")
                if attempt < self.event_retries:
                    self.sleep(self.retry_wait)
        self.log(f"entrega {delivery_id}: evento {event} perdido, o backend não respondeu")
```

(e) trocar `_wait_for_receipt` por

```python
    def _wait_for_receipt(self, delivery_id: int) -> str | None:
        """Espera o solicitante confirmar o recebimento. Devolve None se confirmou, ou o motivo da falha."""
        waited, last_error = 0.0, None
        while True:
            self.hold_if_stopped()
            try:
                status = self.backend.delivery_status(delivery_id)
            except BackendError as err:  # o backend pode estar reiniciando: conta como "ainda não"
                status, last_error = None, str(err)
                self.log(f"entrega {delivery_id}: não consegui consultar o status ({err})")
            if status == "ENTREGUE":
                return None
            if status in ("CANCELADA", "FALHOU"):
                return f"entrega {status.lower()}"
            if waited >= self.receipt_timeout:
                return "recebimento não confirmado a tempo" + (f" ({last_error})" if last_error else "")
            self.sleep(self.poll_interval)
            waited += self.poll_interval
```

Em `node.py`: importar `from .ports import BackendError, NavigationTuner, Navigator`; acrescentar antes de `main`:

```python
def _login_when_available(client: BackendClient, name: str) -> None:
    """Entra no backend; se ele ainda não subiu, espera. Usuário ou senha errados (401) é erro fatal."""
    while True:
        try:
            client.login()
            return
        except BackendError as err:
            if err.status in (401, 403):
                raise SystemExit(str(err))
            print(f"{name}: {err} Tentando de novo em 5 s.", flush=True)
            time.sleep(5)
```

em `main()` trocar os dois `client.login()` / `telemetry_client.login()` por `_login_when_available(client, "dispatcher")` / `_login_when_available(telemetry_client, "telemetria")`, e trocar o laço final por

```python
    try:
        while rclpy.ok():
            try:
                if dispatcher.run_once() is None:
                    time.sleep(2)
            except BackendError as err:  # backend fora do ar entre duas entregas: espera e pergunta de novo
                print(f"backend indisponível: {err}", flush=True)
                time.sleep(5)
    finally:
        rclpy.shutdown()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher/robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS
Run: `source /opt/ros/jazzy/setup.bash && cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher/robot/ros2_ws && colcon build --symlink-install 2>&1 | tail -2 && source install/setup.bash && python3 -c "import geraldo_dispatcher.node"`
Expected: `Summary: 3 packages finished` e nenhum erro de import.

- [ ] **Step 5: Commit**

```bash
git add robot
git commit -m "feat(dispatcher): reenvio de eventos e espera tolerantes a falhas do backend; no espera o backend subir"
```

---

### Task 4: Seeds do backend e waypoints do robô continuam batendo

**Files:**
- Create: `robot/hospital/tests/test_seeds_consistency.py`

**Interfaces:**
- Consumes: `backend/seeds/locais.json` (lista de `{id, name, kind, has_stock, waypoint}`) e `robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml`.

- [ ] **Step 1: Escrever o teste**

```python
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SEEDS = json.loads((ROOT / "backend/seeds/locais.json").read_text(encoding="utf-8"))
WAYPOINTS = yaml.safe_load((ROOT / "robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml").read_text(encoding="utf-8"))["waypoints"]


def test_every_location_has_a_waypoint_the_robot_knows():
    unknown = [loc["id"] for loc in SEEDS if loc["waypoint"] not in WAYPOINTS]
    assert unknown == [], f"locais com waypoint que o robô não conhece: {unknown}. Rode python3 robot/hospital/gen_hospital.py."


def test_every_robot_waypoint_but_the_base_belongs_to_a_location():
    used = {loc["waypoint"] for loc in SEEDS}
    assert sorted(set(WAYPOINTS) - used) == ["base_robo"]


def test_no_two_locations_share_a_waypoint_or_an_id():
    assert len({loc["waypoint"] for loc in SEEDS}) == len(SEEDS)
    assert len({loc["id"] for loc in SEEDS}) == len(SEEDS)
```

- [ ] **Step 2: Rodar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher && python3 -m pytest robot/hospital/tests/test_seeds_consistency.py -q`
Expected: PASS hoje (o teste é uma trava contra regressão). Se falhar, o gerador e as seeds divergiram: rodar `python3 robot/hospital/gen_hospital.py` e conferir o diff antes de seguir.

- [ ] **Step 3: Provar que o teste pega o erro** — `sed -i 's/"waypoint": "cc_entrega"/"waypoint": "cc_entrgea"/' backend/seeds/locais.json && python3 -m pytest robot/hospital/tests/test_seeds_consistency.py -q`; Expected: FAIL citando `centro_cirurgico`; depois `git checkout backend/seeds/locais.json`.

- [ ] **Step 4: Commit**

```bash
git add robot/hospital/tests/test_seeds_consistency.py
git commit -m "test(hospital): seeds do backend e waypoints do robo precisam bater"
```

---

### Task 5: Validador do OpenAPI e exemplos gerados do código

**Files:**
- Create: `robot/scripts/openapi_check.py`
- Create: `robot/scripts/contract_examples.py`
- Create (gerados): `docs/contracts/examples/robot-telemetry.json`, `docs/contracts/examples/robot-events.json`
- Test: `robot/scripts/tests/test_contract_examples.py`

**Interfaces:**
- Produces: `openapi_check.validate(value, schema: dict, spec: dict, path: str = "$") -> list[str]` (lista vazia = válido; trata `$ref`, `nullable`, `enum`, `type`, `format: date-time`, `minimum`, `maximum`, `required`, `properties`, `items`). `contract_examples.telemetry_examples() -> dict[str, dict]` (uma chave por estado), `contract_examples.event_examples() -> dict[str, list[dict]]` (chaves `entrega_concluida`, `falha_na_origem`, `entrega_cancelada`, `recebimento_nao_confirmado`), `contract_examples.EXAMPLES: Path` e `main()` que escreve os dois JSON.

- [ ] **Step 1: Escrever os testes que falham** — criar `robot/scripts/tests/test_contract_examples.py`:

```python
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from robot.scripts.contract_examples import EXAMPLES, event_examples, telemetry_examples  # noqa: E402
from robot.scripts.openapi_check import validate  # noqa: E402

SPEC = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))
SCHEMAS = SPEC["components"]["schemas"]
TELEMETRY = {"robot_state": "IDLE", "pose": {"x": 1.0, "y": 2.0, "yaw": 0.0}, "battery": 80.0, "updated_at": "2026-11-13T12:00:00+00:00"}


def test_there_is_one_telemetry_example_per_state_and_all_follow_the_contract():
    examples = telemetry_examples()
    assert list(examples) == SCHEMAS["Telemetry"]["properties"]["robot_state"]["enum"]
    for state, body in examples.items():
        assert validate(body, SCHEMAS["Telemetry"], SPEC) == [], state
        assert body["robot_state"] == state


def test_every_event_example_follows_the_contract():
    for name, events in event_examples().items():
        for event in events:
            assert validate(event, SCHEMAS["RobotEvent"], SPEC) == [], name


def test_the_event_sequences_are_the_documented_ones():
    examples = event_examples()
    assert [e["event"] for e in examples["entrega_concluida"]] == ["LOADED", "ARRIVED", "UNLOCKED"]
    assert [e["event"] for e in examples["falha_na_origem"]] == ["FAILED"]
    assert [e["event"] for e in examples["entrega_cancelada"]] == ["LOADED", "ARRIVED", "FAILED"]
    assert [e["event"] for e in examples["recebimento_nao_confirmado"]] == ["LOADED", "ARRIVED", "FAILED"]
    assert examples["falha_na_origem"][0]["reason"] == "não chegou à origem"


def test_the_example_files_are_up_to_date():
    assert json.loads((EXAMPLES / "robot-telemetry.json").read_text(encoding="utf-8")) == telemetry_examples()
    assert json.loads((EXAMPLES / "robot-events.json").read_text(encoding="utf-8")) == event_examples()


def test_the_validator_accepts_a_valid_body_and_nullable_fields():
    assert validate({**TELEMETRY, "delivery_id": None}, SCHEMAS["Telemetry"], SPEC) == []


def test_the_validator_catches_each_kind_of_violation():
    schema = SCHEMAS["Telemetry"]
    assert any("fora de" in e for e in validate({**TELEMETRY, "robot_state": "VOANDO"}, schema, SPEC))
    assert any("falta battery" in e for e in validate({k: v for k, v in TELEMETRY.items() if k != "battery"}, schema, SPEC))
    assert any("maior" in e for e in validate({**TELEMETRY, "battery": 120.0}, schema, SPEC))
    assert any("esperado number" in e for e in validate({**TELEMETRY, "battery": "cheia"}, schema, SPEC))
    assert any("esperado number" in e for e in validate({**TELEMETRY, "battery": True}, schema, SPEC))
    assert any("data/hora" in e for e in validate({**TELEMETRY, "updated_at": "ontem"}, schema, SPEC))
    assert any("nulo" in e for e in validate({**TELEMETRY, "battery": None}, schema, SPEC))
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher && python3 -m pytest robot/scripts/tests/test_contract_examples.py -q`
Expected: FAIL (`ModuleNotFoundError: robot.scripts.contract_examples`)

- [ ] **Step 3: Implementar o validador** — `robot/scripts/openapi_check.py`:

```python
"""Validador mínimo de corpos contra os schemas do docs/contracts/openapi.yaml (sem dependência nova).

Cobre só o que o contrato usa: $ref, nullable, enum, type, format date-time, minimum, maximum, required, properties e items.
"""
from datetime import datetime

TYPES = {"string": str, "boolean": bool, "integer": int, "number": (int, float), "object": dict, "array": list}


def validate(value, schema: dict, spec: dict, path: str = "$") -> list[str]:
    """Devolve a lista de violações de `value` contra `schema` (vazia = válido)."""
    if "$ref" in schema:
        node = spec
        for part in schema["$ref"].removeprefix("#/").split("/"):
            node = node[part]
        return validate(value, node, spec, path)
    if value is None:
        return [] if schema.get("nullable") else [f"{path}: nulo não é permitido"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} fora de {schema['enum']}")
    kind = schema.get("type")
    if kind and (not isinstance(value, TYPES[kind]) or (kind in ("integer", "number") and isinstance(value, bool))):
        return errors + [f"{path}: esperado {kind}, veio {type(value).__name__}"]
    if kind == "string" and schema.get("format") == "date-time":
        try:
            datetime.fromisoformat(value)
        except ValueError:
            errors.append(f"{path}: data/hora inválida: {value!r}")
    if kind in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} menor que {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} maior que {schema['maximum']}")
    if kind == "object":
        errors += [f"{path}: falta {name}" for name in schema.get("required", []) if name not in value]
        for name, sub in schema.get("properties", {}).items():
            if name in value:
                errors += validate(value[name], sub, spec, f"{path}.{name}")
    if kind == "array":
        for index, item in enumerate(value):
            errors += validate(item, schema.get("items", {}), spec, f"{path}[{index}]")
    return errors
```

- [ ] **Step 4: Implementar o gerador** — `robot/scripts/contract_examples.py`:

```python
#!/usr/bin/env python3
"""Gera docs/contracts/examples/robot-telemetry.json e robot-events.json a partir do código do robô.

Os exemplos usam o próprio build_telemetry e o próprio Dispatcher, então não saem do que o robô realmente envia.
Os testes conferem que os arquivos estão em dia e seguem o OpenAPI.

Uso: python3 robot/scripts/contract_examples.py
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "robot/ros2_ws/src/geraldo_dispatcher"))

from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
from geraldo_dispatcher.ports import BackendPort, Navigator  # noqa: E402
from geraldo_dispatcher.states import State  # noqa: E402
from geraldo_dispatcher.telemetry import build_telemetry  # noqa: E402
from geraldo_dispatcher.waypoints import Pose  # noqa: E402

EXAMPLES = ROOT / "docs/contracts/examples"
NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
DELIVERY_ID = 7
POSES = {
    "base_robo": Pose(6.5, 26.5, math.radians(270)),
    "farmacia_balcao": Pose(7.0, 24.0, math.radians(270)),
    "cons1_entrega": Pose(14.5, 4.0, math.radians(270)),
}
TASK = {"id": DELIVERY_ID, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega", "priority": "media"}

# estado: (pose, bateria, entrega em curso, rota)
SNAPSHOTS = {
    State.IDLE: (Pose(6.5, 26.5, -1.5708), 100.0, None, []),
    State.CARREGANDO: (Pose(7.0, 24.0, -1.5708), 99.8, DELIVERY_ID, []),
    State.A_CAMINHO: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, [(14.2, 28.9), (20.0, 28.9), (29.0, 28.9)]),
    State.CHEGOU: (Pose(14.5, 4.0, -1.5708), 98.0, DELIVERY_ID, []),
    State.AGUARDANDO_RETIRADA: (Pose(14.5, 4.0, -1.5708), 97.9, DELIVERY_ID, []),
    State.VOLTANDO: (Pose(10.0, 28.9, 3.1416), 97.0, DELIVERY_ID, [(10.0, 28.9), (6.5, 26.5)]),
    State.PARADA_EMERGENCIA: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, []),
}
# cenário: (statuses da entrega que o backend devolve, a origem é inalcançável?)
SCENARIOS = {
    "entrega_concluida": (["ENTREGUE"], False),
    "falha_na_origem": (["ENTREGUE"], True),
    "entrega_cancelada": (["CANCELADA"], False),
    "recebimento_nao_confirmado": (["AGUARDANDO_RECEBIMENTO"], False),
}


class _Backend(BackendPort):
    def __init__(self, statuses) -> None:
        self._statuses, self.events = list(statuses), []

    def next_task(self):
        return dict(TASK)

    def send_event(self, delivery_id, event, reason=None):
        self.events.append({"delivery_id": delivery_id, "event": event, "reason": reason})
        return True

    def delivery_status(self, delivery_id):
        return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]


class _Navigator(Navigator):
    def __init__(self, fails_at) -> None:
        self._fails_at = fails_at

    def go_to(self, pose):
        return pose != self._fails_at


def telemetry_examples() -> dict[str, dict]:
    return {state.value: build_telemetry(state, pose, battery, delivery_id, route, [], NOW)
            for state, (pose, battery, delivery_id, route) in SNAPSHOTS.items()}


def event_examples() -> dict[str, list[dict]]:
    examples = {}
    for name, (statuses, origin_unreachable) in SCENARIOS.items():
        backend = _Backend(statuses)
        navigator = _Navigator(POSES["farmacia_balcao"] if origin_unreachable else None)
        Dispatcher(backend, POSES, navigator, sleep=lambda _: None, receipt_timeout=4.0, log=lambda *_: None).run_once()
        examples[name] = backend.events
    return examples


def main() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    for filename, data in (("robot-telemetry.json", telemetry_examples()), ("robot-events.json", event_examples())):
        (EXAMPLES / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"gerado: {EXAMPLES / filename}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Gerar os arquivos e rodar**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher && python3 robot/scripts/contract_examples.py && python3 -m pytest robot/scripts/tests/test_contract_examples.py -q`
Expected: `gerado:` duas vezes e PASS (6 testes).

- [ ] **Step 6: Commit**

```bash
git add robot/scripts docs/contracts/examples
git commit -m "feat(contratos): exemplos de telemetria e eventos gerados do codigo e validados contra o OpenAPI"
```

---

### Task 6: Protocolo do robô e suíte final

**Files:**
- Create: `docs/contracts/robot-protocol.md`
- Modify: `robot/AGENTS.md`

- [ ] **Step 1: Escrever `docs/contracts/robot-protocol.md`** com exatamente estas seções, em português:

1. **Quem fala com quem** — `geraldo_dispatcher` (Samuel) usa o usuário `robo`; chama o backend (Erik) por HTTP e o Nav2 por ROS; Vieira e Pedro só leem (web, mock).
2. **Sequência de uma entrega** — tabela `passo | estado do robô | chamada ao backend`: (1) `IDLE`: `POST /robot/next-task` (200 com `RobotTask`, 204 fila vazia); (2) `A_CAMINHO` até `origin_waypoint`; (3) `CARREGANDO`: `POST /robot/events` `LOADED`; (4) `A_CAMINHO` até `dest_waypoint`; (5) `CHEGOU`: `ARRIVED`; (6) `AGUARDANDO_RETIRADA`: `GET /deliveries/{id}` a cada 2 s até `ENTREGUE` (o solicitante chama `POST /deliveries/{id}/confirm-receipt`); (7) `UNLOCKED` depois do `ENTREGUE`; (8) `VOLTANDO` à `base_robo`; (9) `IDLE`. O perfil de navegação segue a prioridade da tarefa (crítica 1,0 m/s, média 0,8 m/s, rotina 0,5 m/s).
3. **Falhas** — `FAILED` com `reason`: `não chegou à origem`, `não chegou ao destino`, `entrega cancelada`, `entrega falhou`, `recebimento não confirmado a tempo` (timeout de 300 s; com sufixo `(<erro>)` quando as consultas falharam). Depois de qualquer falha o robô volta à base. O backend pode responder 409 ao evento (por exemplo `FAILED` de entrega já cancelada); o robô só registra no log.
4. **Telemetria** — `POST /robot/telemetry` a cada 1 s com o corpo de `Telemetry`; `route` com no máximo 50 pontos (do `/plan` do Nav2); `obstacles` é sempre `[]` por enquanto; `battery` é virtual (gasta andando, recarrega parado na base); o backend ignora `updated_at` e grava a hora de recebimento; sem pose do AMCL ainda, o robô não envia.
5. **Emergência** — `/geraldo/estop` (`std_msgs/Bool`) é tópico ROS, não HTTP; com `true` o estado vira `PARADA_EMERGENCIA` em cerca de 1 s e a telemetria passa a refletir isso; ao liberar, volta ao estado anterior e refaz a mesma meta.
6. **Resiliência** — evento não enviado: 3 tentativas com 1 s entre elas, depois segue sem ele; consulta do status que falha conta como "ainda não"; backend fora do ar entre entregas: o robô espera 5 s e pergunta de novo; usuário ou senha errados no login é erro fatal. `uvicorn --reload` do Erik não derruba o robô.
7. **Exemplos** — `docs/contracts/examples/robot-telemetry.json` (um por estado) e `robot-events.json` (4 cenários), gerados por `python3 robot/scripts/contract_examples.py` e validados contra o OpenAPI por teste.
8. **O que cada frente precisa fazer** — **Erik:** (a) `GET /deliveries/{id}` precisa aceitar o papel `robo` (no plano da semana 1 só `admin`, `farmaceutico` e o solicitante veem; sem isso toda entrega termina em `FAILED` após 5 min); (b) implementar `POST /robot/telemetry` (204, papel `robo`, 403 para os outros, 422 para corpo inválido) e repassar no `GET /telemetry` e no WebSocket; (c) `ARRIVED` leva a entrega a `AGUARDANDO_RECEBIMENTO`; `UNLOCKED` chega depois de `ENTREGUE` e deve ser aceito (ou responder 409, que o robô tolera); (d) `POST /robot/next-task` deve pular `rotina` fora da janela de baixo pico (o robô não consegue devolver uma tarefa já entregue). **Vieira:** montar o MSW e as telas de estado do robô com os exemplos; o botão "confirmar recebimento" só faz sentido com `status = AGUARDANDO_RECEBIMENTO`; `obstacles` vem vazio. **Pedro:** o `tools/mock_robot.py` deve seguir a sequência da seção 2 e usar os eventos de `robot-events.json`; o teste de contrato precisa incluir a operação `POST /robot/telemetry` (nova no OpenAPI) na lista de pendentes até o Erik implementar; o ataque "obstáculo falso na telemetria" mira `POST /robot/telemetry` (mitigações: papel `robo`, estado no enum, bateria de 0 a 100, `updated_at` ignorado).

- [ ] **Step 2: Apontar o protocolo em `robot/AGENTS.md`** — depois do bullet "Dispatcher:", acrescentar:

```markdown
- Protocolo com o backend, a web e o mock: `docs/contracts/robot-protocol.md`. Os exemplos de telemetria e de eventos (`docs/contracts/examples/`) são gerados por `python3 robot/scripts/contract_examples.py`; rode de novo ao mudar `build_telemetry`, os eventos ou os estados (o teste `test_contract_examples.py` falha se ficarem velhos).
```

- [ ] **Step 3: Suíte final**

Run: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/dispatcher && python3 -m pytest tools robot -q && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q)`
Expected: PASS nos dois.

- [ ] **Step 4: Commit**

```bash
git add docs/contracts/robot-protocol.md robot/AGENTS.md
git commit -m "docs(contratos): protocolo do robo e avisos para Erik, Vieira e Pedro"
```
