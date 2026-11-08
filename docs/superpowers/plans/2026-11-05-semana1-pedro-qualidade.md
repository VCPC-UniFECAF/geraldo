# G.E.R.A.L.D.O. — Semana 1 (Pedro): qualidade, CI e robô de mentira

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Montar a rede de segurança do projeto: CI no GitHub que roda os testes de cada área, um teste que garante que o backend cumpre o contrato da API, um robô de mentira que consome a fila do backend sem precisar do Gazebo, e uma coleção de requests para testar à mão.

**Architecture:** O CI tem um job por área e cada job só roda quando a área já existe (assim fica verde desde o primeiro dia). O teste de contrato compara `docs/contracts/openapi.yaml` com o OpenAPI que o backend gera e mantém uma lista `PENDING` que só encolhe. O robô de mentira é uma classe pequena (`MockRobot`) que recebe um `httpx.Client`, então roda tanto contra o servidor quanto dentro dos testes.

**Tech Stack:** GitHub Actions, Python 3.12, pytest, httpx, PyYAML.

**Spec:** `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` (seções 4.4, 6 e 7)

**Pré-requisitos:** Tarefa 2 do plano de fundação (contratos em `docs/contracts/openapi.yaml`). As Tarefas 2 e 3 deste plano usam o backend do Erik (Tarefa 4 do plano dele); até lá, faça as tarefas 1 e 4 e use o PR do Erik.

## Global Constraints

- Contrato é lei: `docs/contracts/openapi.yaml`. Pedro **não muda** o contrato; se achar erro, abre PR em `docs/contracts/` e avisa o Samuel (spec §6).
- Testes e ataques só contra `localhost` (`security/AGENTS.md`).
- Nenhuma senha ou segredo no repositório: o robô de mentira lê a senha de `GERALDO_ROBOT_PASSWORD` (ou `GERALDO_DEMO_PASSWORD`).
- Papel `robo` é o único que chama `/robot/next-task` (spec §6.1).
- Padrões (`docs/padroes-de-projeto.md`): o `MockRobot` recebe o `httpx.Client` e o `sleep` pelo construtor (DIP), então roda contra o servidor e dentro dos testes sem mudar nada. Os métodos `login`, `next_task` e `report` têm os mesmos nomes do `BackendClient` do robô real, e o robô de mentira e o `tools/fake_backend.py` do Samuel obedecem ao mesmo contrato do backend verdadeiro (LSP); é isso que o teste de contrato garante.
- Pedro testa as frentes dos outros; **não** implementa funcionalidade do backend, da web nem do robô.
- Commits em português, curtos; branch `feat/qualidade-<assunto>`; nada direto na `main`.

---

### Task 1: CI no GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tools/tests/test_ci_workflow.py`

**Interfaces:**
- Produces: workflow `CI` com os jobs `tools`, `backend`, `web` e `design-system`. Os jobs `backend`, `web` e `design-system` só executam os passos quando a pasta da área tem o arquivo-âncora (`backend/requirements.txt`, `web/package.json`, `design-system/tokens/build.mjs`).

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_ci_workflow.py`:

```python
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def load() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def triggers(wf: dict) -> dict:
    # PyYAML lê a chave `on` como o booleano True
    return wf.get("on", wf.get(True))


def test_runs_on_push_to_main_and_on_pull_requests():
    t = triggers(load())
    assert t["push"]["branches"] == ["main"]
    assert "pull_request" in t


def test_has_one_job_per_area():
    assert set(load()["jobs"]) == {"tools", "backend", "web", "design-system"}


def test_every_job_checks_out_the_repository_first():
    for name, job in load()["jobs"].items():
        assert job["steps"][0]["uses"].startswith("actions/checkout@"), name


def test_area_jobs_only_run_steps_when_the_area_exists():
    anchors = {"backend": "backend/requirements.txt", "web": "web/package.json", "design-system": "design-system/tokens/build.mjs"}
    for name, anchor in anchors.items():
        steps = load()["jobs"][name]["steps"][1:]
        runnable = [s for s in steps if "run" in s]
        assert runnable, name
        for step in runnable:
            assert anchor in step.get("if", ""), f"{name}: passo sem condição de existência: {step['run']}"


def test_backend_job_runs_the_backend_tests():
    runs = " ".join(s.get("run", "") for s in load()["jobs"]["backend"]["steps"])
    assert "python -m pytest" in runs


def test_generated_files_must_be_committed():
    runs = " ".join(s.get("run", "") for j in load()["jobs"].values() for s in j["steps"])
    assert "git diff --exit-code" in runs
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_ci_workflow.py -q`
Expected: FAIL (`ci.yml` não existe).

- [ ] **Step 3: Escrever o workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  tools:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install numpy pyyaml pytest openapi-spec-validator httpx
      - run: python -m pytest tools -q
      - run: python -m openapi_spec_validator docs/contracts/openapi.yaml
      - name: Arquivos gerados do hospital precisam estar commitados
        run: |
          python tools/gen_hospital.py
          git diff --exit-code

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - if: hashFiles('backend/requirements.txt') != ''
        run: pip install -r backend/requirements.txt
      - if: hashFiles('backend/requirements.txt') != ''
        run: cd backend && python -m pytest -q

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - if: hashFiles('web/package.json') != ''
        run: cd web && npm ci
      - if: hashFiles('web/package.json') != ''
        run: cd web && npm test -- --run
      - if: hashFiles('web/package.json') != ''
        run: cd web && npm run build

  design-system:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - if: hashFiles('design-system/tokens/build.mjs') != ''
        run: cd design-system && node --test
      - name: dist/ precisa estar commitado e atualizado
        if: hashFiles('design-system/tokens/build.mjs') != ''
        run: |
          node design-system/tokens/build.mjs
          git diff --exit-code
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tools/tests/test_ci_workflow.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Commit, abrir o PR e conferir no GitHub**

```bash
git checkout -b feat/qualidade-ci
git add .github tools/tests/test_ci_workflow.py
git commit -m "feat(ci): workflow com um job por area"
git push -u origin HEAD
```

Abra o PR e confira na aba **Actions** que os 4 jobs ficaram verdes (os de `backend`, `web` e `design-system` passam sem fazer nada enquanto a área não existe). Se o job `tools` falhar no passo "Arquivos gerados do hospital", o arquivo gerado no repo está desatualizado: avise o Samuel.

---

### Task 2: Teste de contrato da API

**Files:**
- Create: `backend/tests/test_contract.py`

**Interfaces:**
- Consumes: `docs/contracts/openapi.yaml` e `app.main.app` (backend do Erik, com as rotas da semana 1).
- Produces: um teste que falha se (a) uma operação do contrato some sem estar em `PENDING`, (b) o backend expõe operação fora do contrato, (c) os códigos de sucesso (2xx) divergem do contrato. `PENDING` lista o que ainda falta e **só encolhe**.

- [ ] **Step 1: Escrever o teste**

Create `backend/tests/test_contract.py`:

```python
import re
from pathlib import Path

import yaml

from app.main import app

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "openapi.yaml"
METHODS = {"get", "post", "put", "delete", "patch"}

# Operações do contrato que o backend ainda não implementa. Só encolhe; quando o Erik
# implementar uma, remova-a daqui (o teste test_pending_has_no_implemented_operation cobra isso).
PENDING = {
    ("post", "/deliveries/{}/cancel"),
    ("post", "/deliveries/{}/approve"),
    ("post", "/deliveries/{}/confirm-receipt"),
    ("get", "/movements"),
    ("post", "/robot/events"),
    ("get", "/telemetry"),
}


def norm(path: str) -> str:
    """Compara rotas ignorando o nome do parâmetro de caminho ({id} x {delivery_id})."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def operations(spec: dict) -> dict:
    return {
        (method, norm(path)): op
        for path, ops in spec["paths"].items()
        for method, op in ops.items()
        if method in METHODS
    }


def success_codes(op: dict) -> set:
    return {code for code in op["responses"] if str(code).startswith("2")}


contract = operations(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))
implemented = operations(app.openapi())


def test_every_contract_operation_is_implemented_or_pending():
    missing = set(contract) - set(implemented)
    assert missing == PENDING, f"faltando fora do PENDING: {missing - PENDING}; já implementadas no PENDING: {PENDING - missing}"


def test_pending_has_no_implemented_operation():
    assert not (PENDING & set(implemented)), "remova de PENDING o que já foi implementado"


def test_backend_exposes_nothing_outside_the_contract():
    assert not (set(implemented) - set(contract)), set(implemented) - set(contract)


def test_success_status_codes_follow_the_contract():
    for key in set(contract) & set(implemented):
        assert str(sorted(success_codes(implemented[key]))) == str(sorted(success_codes(contract[key]))), key
```

- [ ] **Step 2: Rodar**

Run (em `backend/`): `python -m pytest tests/test_contract.py -q`
Expected: `4 passed` se o backend do Erik está como no plano dele. Se falhar:
- "faltando fora do PENDING": o backend não implementou uma rota que o contrato exige. Avise o Erik.
- "fora do contrato": o backend criou rota que o contrato não tem. Avise o Erik e o Samuel; ou vira PR no contrato, ou a rota sai.
- código de sucesso diferente: confira `status_code=` e `responses=` na rota (ex.: criar entrega deve ser `201`, `next-task` vazia `204`).

- [ ] **Step 3: Provar que o teste pega problemas (mutação rápida)**

Edite temporariamente `backend/app/routers/deliveries.py`, trocando `status_code=201` por `status_code=200`. Rode o teste: deve falhar em `test_success_status_codes_follow_the_contract` apontando `('post', '/deliveries')`. Desfaça com `git checkout backend/app/routers/deliveries.py`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_contract.py
git commit -m "test(backend): teste de contrato contra o openapi.yaml"
```

---

### Task 3: Robô de mentira

**Files:**
- Create: `tools/mock_robot.py`
- Test: `tools/tests/test_mock_robot.py`, `backend/tests/test_mock_robot_integration.py`

**Interfaces:**
- Consumes: API do backend (`POST /auth/login`, `POST /robot/next-task`; `POST /robot/events` na semana 2).
- Produces:
  - `tools.mock_robot.MockRobot(client, username="robo", password=...)` com `login()`, `next_task() -> dict | None`, `report(delivery_id, event) -> dict` e `run_once(travel_seconds=0.0, report=False, sleep=time.sleep) -> dict | None`.
  - CLI: `python tools/mock_robot.py --api http://localhost:8000 --travel 5 [--report] [--once]`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Create `tools/tests/test_mock_robot.py`:

```python
import json

import httpx
import pytest

from tools.mock_robot import MockRobot

TASK = {"id": 7, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega", "status": "EM_ROTA"}


def make_client(tasks, calls):
    queue = list(tasks)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("authorization"), request.content))
        if request.url.path == "/auth/login":
            body = json.loads(request.content)
            if body["password"] != "certa":
                return httpx.Response(401, json={"detail": "Usuário ou senha incorretos. Tente de novo."})
            return httpx.Response(200, json={"access_token": "tok123", "token_type": "bearer"})
        if request.url.path == "/robot/next-task":
            return httpx.Response(200, json=queue.pop(0)) if queue else httpx.Response(204)
        if request.url.path == "/robot/events":
            return httpx.Response(200, json={"id": json.loads(request.content)["delivery_id"], "status": "ok"})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://api.test")


def test_login_sets_the_bearer_token():
    calls = []
    robot = MockRobot(make_client([], calls), "robo", "certa")
    robot.login()
    robot.next_task()
    assert calls[-1][2] == "Bearer tok123"


def test_login_failure_raises_a_clear_error():
    robot = MockRobot(make_client([], []), "robo", "errada")
    with pytest.raises(RuntimeError, match="Login do robô falhou"):
        robot.login()


def test_next_task_returns_none_when_the_queue_is_empty():
    robot = MockRobot(make_client([], []), "robo", "certa")
    robot.login()
    assert robot.next_task() is None


def test_run_once_waits_the_travel_time_and_does_not_report_by_default():
    calls, slept = [], []
    robot = MockRobot(make_client([TASK], calls), "robo", "certa")
    robot.login()
    assert robot.run_once(travel_seconds=4.5, sleep=slept.append) == TASK
    assert slept == [4.5]
    assert all(path != "/robot/events" for _, path, _, _ in calls)


def test_run_once_with_report_sends_the_events_in_order():
    calls = []
    robot = MockRobot(make_client([TASK], calls), "robo", "certa")
    robot.login()
    robot.run_once(report=True, sleep=lambda s: None)
    events = [json.loads(c[3])["event"] for c in calls if c[1] == "/robot/events"]
    assert events == ["LOADED", "ARRIVED", "UNLOCKED"]
    assert all(json.loads(c[3])["delivery_id"] == 7 for c in calls if c[1] == "/robot/events")


def test_run_once_returns_none_on_empty_queue():
    robot = MockRobot(make_client([], []), "robo", "certa")
    robot.login()
    assert robot.run_once(sleep=lambda s: None) is None
```

Create `backend/tests/test_mock_robot_integration.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.mock_robot import MockRobot  # noqa: E402

from tests.conftest import PASSWORD  # noqa: E402


def test_mock_robot_claims_tasks_from_the_real_api(client, auth):
    body = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 3}], "priority": "media"}
    assert client.post("/deliveries", json=body, headers=auth("medico1")).status_code == 201
    robot = MockRobot(client, "robo", PASSWORD)  # o TestClient é um httpx.Client
    client.headers.pop("authorization", None)
    robot.login()
    task = robot.run_once(sleep=lambda s: None)
    assert task["origin_waypoint"] == "farmacia_balcao"
    assert task["dest_waypoint"] == "cons1_entrega"
    assert task["status"] == "EM_ROTA"
    assert robot.run_once(sleep=lambda s: None) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_mock_robot.py -q`
Expected: FAIL (`tools.mock_robot` não existe).

- [ ] **Step 3: Implementar**

Create `tools/mock_robot.py`:

```python
#!/usr/bin/env python3
"""Robô de mentira: consome a fila do backend sem precisar do Gazebo.

Uso:
  GERALDO_ROBOT_PASSWORD=... python tools/mock_robot.py --api http://localhost:8000 --travel 5
Na semana 2, com POST /robot/events no backend, use --report para enviar LOADED, ARRIVED e UNLOCKED.
"""
import argparse
import os
import time

import httpx

EVENTS = ("LOADED", "ARRIVED", "UNLOCKED")


class MockRobot:
    def __init__(self, client: httpx.Client, username: str = "robo", password: str = "") -> None:
        self.client = client
        self.username = username
        self.password = password

    def login(self) -> None:
        r = self.client.post("/auth/login", json={"username": self.username, "password": self.password})
        if r.status_code != 200:
            raise RuntimeError(f"Login do robô falhou ({r.status_code}): {r.text}")
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def next_task(self) -> dict | None:
        r = self.client.post("/robot/next-task")
        if r.status_code == 204:
            return None
        r.raise_for_status()
        return r.json()

    def report(self, delivery_id: int, event: str) -> dict:
        r = self.client.post("/robot/events", json={"delivery_id": delivery_id, "event": event})
        r.raise_for_status()
        return r.json()

    def run_once(self, travel_seconds: float = 0.0, report: bool = False, sleep=time.sleep) -> dict | None:
        task = self.next_task()
        if task is None:
            return None
        print(f"entrega {task['id']}: {task['origin_waypoint']} -> {task['dest_waypoint']}")
        sleep(travel_seconds)
        if report:
            for event in EVENTS:
                self.report(task["id"], event)
        return task


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--user", default="robo")
    ap.add_argument("--travel", type=float, default=5.0, help="segundos simulando o trajeto")
    ap.add_argument("--report", action="store_true", help="envia os eventos para /robot/events")
    ap.add_argument("--once", action="store_true", help="processa no máximo uma entrega e sai")
    a = ap.parse_args()
    password = os.environ.get("GERALDO_ROBOT_PASSWORD") or os.environ.get("GERALDO_DEMO_PASSWORD")
    if not password:
        raise SystemExit("Defina GERALDO_ROBOT_PASSWORD (ou GERALDO_DEMO_PASSWORD) com a senha do usuário do robô.")
    with httpx.Client(base_url=a.api, timeout=10) as client:
        robot = MockRobot(client, a.user, password)
        robot.login()
        while True:
            task = robot.run_once(a.travel, a.report)
            if a.once:
                break
            if task is None:
                time.sleep(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tools/tests/test_mock_robot.py -q && cd backend && python -m pytest tests/test_mock_robot_integration.py -q`
Expected: `6 passed` e `1 passed`.

- [ ] **Step 5: Conferir contra o servidor de verdade**

Com o backend rodando (`uvicorn app.main:app`, `GERALDO_DEMO_PASSWORD` definido) e uma entrega criada (veja o passo 5 da Tarefa 5 do plano do Erik):

```bash
GERALDO_ROBOT_PASSWORD="$GERALDO_DEMO_PASSWORD" python tools/mock_robot.py --travel 1 --once
```

Expected: imprime `entrega 1: farmacia_balcao -> cons1_entrega`.

- [ ] **Step 6: Commit**

```bash
git add tools/mock_robot.py tools/tests/test_mock_robot.py backend/tests/test_mock_robot_integration.py
git commit -m "feat(tools): robo de mentira para consumir a fila do backend"
```

---

### Task 4: Coleção de requests para teste manual

**Files:**
- Create: `security/requests/semana1.http`, `security/requests/README.md`
- Test: `tools/tests/test_requests_collection.py`

**Interfaces:**
- Consumes: rotas da semana 1 do contrato.
- Produces: arquivo `.http` (VS Code com a extensão REST Client, ou o cliente HTTP do JetBrains) com uma requisição por rota e as variáveis `@baseUrl` e `@password`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_requests_collection.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECTION = ROOT / "security/requests/semana1.http"

WEEK1_ROUTES = [
    "POST {{baseUrl}}/auth/login",
    "GET {{baseUrl}}/me",
    "GET {{baseUrl}}/locations",
    "GET {{baseUrl}}/stock",
    "POST {{baseUrl}}/deliveries",
    "GET {{baseUrl}}/deliveries",
    "POST {{baseUrl}}/robot/next-task",
]


def test_every_week1_route_has_a_request():
    text = COLLECTION.read_text(encoding="utf-8")
    missing = [r for r in WEEK1_ROUTES if r not in text]
    assert not missing, missing


def test_no_credentials_are_hardcoded():
    text = COLLECTION.read_text(encoding="utf-8")
    assert "@password = {{$dotenv GERALDO_DEMO_PASSWORD}}" in text
    assert "Bearer eyJ" not in text
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_requests_collection.py -q`
Expected: FAIL (arquivo não existe).

- [ ] **Step 3: Escrever a coleção**

Create `security/requests/semana1.http`:

```http
# Coleção da semana 1 (backend em localhost). Extensão "REST Client" do VS Code.
# A senha vem do arquivo .env (não versionado) com a linha: GERALDO_DEMO_PASSWORD=...
@baseUrl = http://localhost:8000
@password = {{$dotenv GERALDO_DEMO_PASSWORD}}

### Login do médico 1 (guarda o token)
# @name loginMedico
POST {{baseUrl}}/auth/login
Content-Type: application/json

{ "username": "medico1", "password": "{{password}}" }

###
@token = {{loginMedico.response.body.access_token}}

### Quem sou eu
GET {{baseUrl}}/me
Authorization: Bearer {{token}}

### Locais
GET {{baseUrl}}/locations
Authorization: Bearer {{token}}

### Estoque da farmácia
GET {{baseUrl}}/stock?location_id=farmacia
Authorization: Bearer {{token}}

### Solicitar medicamento (destino padrão = consultório do usuário)
POST {{baseUrl}}/deliveries
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "origin_id": "farmacia",
  "items": [{ "item_id": "dipirona-500mg", "quantity": 5 }],
  "priority": "media"
}

### Minhas entregas
GET {{baseUrl}}/deliveries
Authorization: Bearer {{token}}

### Login do robô
# @name loginRobo
POST {{baseUrl}}/auth/login
Content-Type: application/json

{ "username": "robo", "password": "{{password}}" }

###
@robotToken = {{loginRobo.response.body.access_token}}

### O robô pede a próxima tarefa (204 se a fila estiver vazia)
POST {{baseUrl}}/robot/next-task
Authorization: Bearer {{robotToken}}
```

Create `security/requests/README.md`:

```markdown
# Coleção de requests

`semana1.http` roda no VS Code com a extensão **REST Client** (ou no cliente HTTP do JetBrains).

1. Suba o backend (`uvicorn app.main:app`) com `GERALDO_DEMO_PASSWORD` definido.
2. Crie um arquivo `.env` na raiz (já ignorado pelo Git) com `GERALDO_DEMO_PASSWORD=<a mesma senha>`.
3. Abra `semana1.http` e clique em **Send Request** acima de cada bloco, de cima para baixo.

Só contra `localhost`.
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tools/tests/test_requests_collection.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit e PR**

```bash
git add security/requests tools/tests/test_requests_collection.py
git commit -m "feat(security): colecao de requests da semana 1"
git push
```

Abra um PR único com as quatro tarefas (ou um por tarefa, se preferir). Na semana 2, este plano continua com os scripts de ataque (`security/attacks/`) e os testes de contrato das rotas novas.
