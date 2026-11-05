# G.E.R.A.L.D.O. — Semana 1 (Erik): backend de gestão hospitalar

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ter uma API FastAPI com login JWT, locais e estoque, criação de entrega com reserva de estoque (padrão Command) e a fila de prioridade que o robô consulta, tudo com testes.

**Architecture:** FastAPI + SQLModel (SQLite). O domínio fica em `app/commands/` (um comando por ação, método `execute()`); os routers só validam a entrada, chamam o comando e traduzem as exceções do domínio em HTTP. O estoque muda **somente** por `Movimentacao` (registro imutável). O banco de testes é SQLite em memória, criado a cada teste.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, PyJWT, pytest, httpx.

**Spec:** `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` (seções 4.2, 5 e 6); contrato: `docs/contracts/openapi.yaml` e `docs/contracts/jwt.md`.

## Global Constraints

- Contrato é lei: rotas, campos, enums e status HTTP de `docs/contracts/openapi.yaml`. Mudança só por PR em `docs/contracts/` com aviso ao Samuel.
- JWT: somente **HS256**; exigir `exp`, `sub`, `role`, `jti`; segredo vem de `GERALDO_JWT_SECRET` (nunca do repositório); expiração padrão de 60 minutos.
- Estoque só muda por `Movimentacao`; `quantity` do movimento é sempre positiva e o tipo (`RESERVA`, `BAIXA`, `CREDITO`, `ESTORNO`) dá a direção.
- Prioridade: `critica` < `media` < `rotina`; dentro da mesma, FIFO por `id`. `critica` nasce em `PENDENTE_APROVACAO`.
- Papéis que criam entrega: `medico`, `enfermeiro`, `farmaceutico`, `admin`. Só `robo` chama `/robot/next-task`.
- Mensagens de erro em português: o que houve e o que fazer.
- Locais sem `waypoint` (ex.: recepção) não recebem nem originam entregas do robô.
- Nenhum segredo no repositório; a senha dos usuários de demonstração vem de `GERALDO_DEMO_PASSWORD`.

---

### Task 1: Projeto FastAPI e health check

**Files:**
- Create: `backend/requirements.txt`, `backend/pytest.ini`, `backend/app/__init__.py`, `backend/app/main.py`
- Test: `backend/tests/__init__.py`, `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.main.app` (instância FastAPI) e `GET /health` (fora do contrato; `include_in_schema=False`).

- [ ] **Step 1: Criar o ambiente e a estrutura**

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
mkdir -p app tests
touch app/__init__.py tests/__init__.py
```

Create `backend/requirements.txt`:

```
fastapi>=0.110
uvicorn[standard]>=0.29
sqlmodel>=0.0.16
pyjwt>=2.8
httpx>=0.27
pytest>=8
pyyaml>=6
```

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
```

Run: `pip install -r requirements.txt`

- [ ] **Step 2: Escrever o teste (falha primeiro)**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_is_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_health.py -q`
Expected: FAIL (`app.main` não existe).

- [ ] **Step 4: Implementar**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0")


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_health.py -q`
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend
git commit -m "feat(backend): projeto FastAPI e health check"
```

---

### Task 2: Configuração, modelos, banco, hash de senha e seed

**Files:**
- Create: `backend/app/config.py`, `backend/app/models.py`, `backend/app/db.py`, `backend/app/security.py`, `backend/app/seed.py`
- Create: `backend/seeds/itens.json`, `backend/seeds/estoque.json`
- Create (fixtures de teste): `backend/tests/fixtures/seeds/locais.json`, `backend/tests/fixtures/seeds/itens.json`, `backend/tests/fixtures/seeds/estoque.json`
- Test: `backend/tests/conftest.py`, `backend/tests/test_seed.py`, `backend/tests/test_password.py`

**Interfaces:**
- Produces (usados nas tarefas 3 a 5):
  - `app.config.settings` com atributos mutáveis: `database_url`, `jwt_secret`, `jwt_minutes`, `demo_password`, `password_iterations`, `auto_seed`.
  - Enums em `app.models`: `Role`, `Priority`, `DeliveryStatus`, `MovementType` (valores iguais ao contrato).
  - Tabelas: `User(id, username, password_hash, role, local_id)`, `Location(id, name, kind, has_stock, waypoint)`, `Item(id, name, unit)`, `Stock(location_id, item_id, quantity, reserved, minimum)` (chave composta nessa ordem), `Delivery(id, origin_id, dest_id, priority, status, requested_by, created_at)`, `DeliveryItem(id, delivery_id, item_id, quantity)`, `Movement(id, delivery_id, type, item_id, location_id, quantity, created_at)`.
  - `app.db.make_engine(url)`, `create_db(engine=None)`, `get_session()` (dependência FastAPI), `engine`.
  - `app.security.hash_password(password, *, salt=None, iterations=None) -> str` e `verify_password(password, stored) -> bool`.
  - `app.seed.seed(session, seeds_dir=SEEDS)` (idempotente; não sobrescreve estoque existente) e `DEMO_USERS`.

- [ ] **Step 1: Escrever as fixtures de teste e os testes (falham primeiro)**

Create `backend/tests/fixtures/seeds/locais.json`:

```json
[
  {"id": "farmacia", "name": "Farmácia central", "kind": "pharmacy", "has_stock": true, "waypoint": "farmacia_balcao"},
  {"id": "banco_sangue", "name": "Banco de sangue", "kind": "blood_bank", "has_stock": true, "waypoint": "banco_sangue_retirada"},
  {"id": "consultorio1", "name": "Consultório 1", "kind": "office", "has_stock": true, "waypoint": "cons1_entrega"},
  {"id": "consultorio2", "name": "Consultório 2", "kind": "office", "has_stock": true, "waypoint": "cons2_entrega"},
  {"id": "enfermaria214", "name": "Enfermaria 214", "kind": "ward", "has_stock": true, "waypoint": "enf214_entrega"},
  {"id": "recepcao", "name": "Recepção", "kind": "reception", "has_stock": false, "waypoint": null}
]
```

Create `backend/tests/fixtures/seeds/itens.json`:

```json
[
  {"id": "dipirona-500mg", "name": "Dipirona 500 mg", "unit": "caixa"},
  {"id": "bolsa-sangue-o-neg", "name": "Bolsa de sangue O negativo", "unit": "bolsa"}
]
```

Create `backend/tests/fixtures/seeds/estoque.json`:

```json
[
  {"location_id": "farmacia", "item_id": "dipirona-500mg", "quantity": 420, "minimum": 100},
  {"location_id": "banco_sangue", "item_id": "bolsa-sangue-o-neg", "quantity": 6, "minimum": 10},
  {"location_id": "consultorio1", "item_id": "dipirona-500mg", "quantity": 0, "minimum": 20}
]
```

Create `backend/tests/conftest.py` (versão da Tarefa 2; a Tarefa 3 a estende):

```python
from pathlib import Path

import pytest
from sqlmodel import Session

from app.config import settings
from app.db import create_db, make_engine
from app.seed import seed

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
PASSWORD = "senha-de-teste"


@pytest.fixture(autouse=True)
def test_settings():
    names = ("jwt_secret", "jwt_minutes", "demo_password", "password_iterations", "auto_seed")
    old = {n: getattr(settings, n) for n in names}
    settings.jwt_secret = "segredo-de-teste-com-mais-de-32-bytes-0123456789"
    settings.jwt_minutes = 60
    settings.demo_password = PASSWORD
    settings.password_iterations = 1000
    settings.auto_seed = False
    yield
    for n, v in old.items():
        setattr(settings, n, v)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    create_db(eng)
    with Session(eng) as s:
        seed(s, FIXTURES)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
```

Create `backend/tests/test_password.py`:

```python
from app.security import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    stored = hash_password("abc123", iterations=1000)
    assert stored.startswith("pbkdf2_sha256$1000$")
    assert verify_password("abc123", stored)
    assert not verify_password("outra", stored)


def test_same_password_gets_different_salts():
    assert hash_password("abc123", iterations=1000) != hash_password("abc123", iterations=1000)


def test_malformed_hash_is_rejected_not_crashed():
    assert not verify_password("abc123", "isto-nao-e-um-hash")
    assert not verify_password("abc123", "md5$1$00$00")
```

Create `backend/tests/test_seed.py`:

```python
from sqlmodel import select

from app.models import Item, Location, Role, Stock, User
from app.seed import seed
from tests.conftest import FIXTURES, PASSWORD


def test_seed_creates_locations_items_stock_and_users(session):
    assert session.get(Location, "farmacia").waypoint == "farmacia_balcao"
    assert session.get(Location, "recepcao").waypoint is None
    assert session.get(Item, "dipirona-500mg").name == "Dipirona 500 mg"
    stock = session.get(Stock, ("farmacia", "dipirona-500mg"))
    assert (stock.quantity, stock.reserved, stock.minimum) == (420, 0, 100)
    medico = session.exec(select(User).where(User.username == "medico1")).one()
    assert medico.role == Role.medico and medico.local_id == "consultorio1"
    assert session.exec(select(User).where(User.username == "robo")).one().role == Role.robo


def test_passwords_are_stored_hashed(session):
    user = session.exec(select(User).where(User.username == "medico1")).one()
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("pbkdf2_sha256$")


def test_seed_is_idempotent_and_never_overwrites_stock(session):
    stock = session.get(Stock, ("farmacia", "dipirona-500mg"))
    stock.quantity = 7
    session.add(stock)
    session.commit()
    seed(session, FIXTURES)
    assert session.get(Stock, ("farmacia", "dipirona-500mg")).quantity == 7
    assert len(session.exec(select(User)).all()) == 6
    assert len(session.exec(select(Location)).all()) == 6
```

- [ ] **Step 2: Rodar e ver falhar**

Run (em `backend/`): `python -m pytest -q`
Expected: FAIL (módulos `app.config`, `app.models`... não existem).

- [ ] **Step 3: Implementar `config.py` e `models.py`**

Create `backend/app/config.py`:

```python
import os
import secrets


class Settings:
    """Configuração lida do ambiente. Atributos mutáveis para os testes."""

    def __init__(self) -> None:
        self.database_url = os.environ.get("GERALDO_DATABASE_URL", "sqlite:///./geraldo.db")
        # sem segredo no ambiente, gera um aleatório (tokens deixam de valer ao reiniciar)
        self.jwt_secret = os.environ.get("GERALDO_JWT_SECRET") or secrets.token_hex(32)
        self.jwt_minutes = int(os.environ.get("GERALDO_JWT_MINUTES", "60"))
        self.demo_password = os.environ.get("GERALDO_DEMO_PASSWORD", "demo-only-change-me")
        self.password_iterations = 200_000
        self.auto_seed = os.environ.get("GERALDO_AUTO_SEED", "1") == "1"


settings = Settings()
```

Create `backend/app/models.py`:

```python
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class Role(str, Enum):
    medico = "medico"
    enfermeiro = "enfermeiro"
    farmaceutico = "farmaceutico"
    admin = "admin"
    robo = "robo"


class Priority(str, Enum):
    critica = "critica"
    media = "media"
    rotina = "rotina"


class DeliveryStatus(str, Enum):
    PENDENTE_APROVACAO = "PENDENTE_APROVACAO"
    NA_FILA = "NA_FILA"
    EM_ROTA = "EM_ROTA"
    AGUARDANDO_RECEBIMENTO = "AGUARDANDO_RECEBIMENTO"
    ENTREGUE = "ENTREGUE"
    CANCELADA = "CANCELADA"
    FALHOU = "FALHOU"


class MovementType(str, Enum):
    RESERVA = "RESERVA"
    BAIXA = "BAIXA"
    CREDITO = "CREDITO"
    ESTORNO = "ESTORNO"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: Role
    local_id: str | None = Field(default=None, foreign_key="location.id")


class Location(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    kind: str
    has_stock: bool = False
    waypoint: str | None = None


class Item(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    unit: str


class Stock(SQLModel, table=True):
    location_id: str = Field(foreign_key="location.id", primary_key=True)
    item_id: str = Field(foreign_key="item.id", primary_key=True)
    quantity: int = 0
    reserved: int = 0
    minimum: int = 0


class Delivery(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    origin_id: str = Field(foreign_key="location.id")
    dest_id: str = Field(foreign_key="location.id")
    priority: Priority
    status: DeliveryStatus
    requested_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)


class DeliveryItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    delivery_id: int = Field(foreign_key="delivery.id", index=True)
    item_id: str = Field(foreign_key="item.id")
    quantity: int


class Movement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    delivery_id: int | None = Field(default=None, foreign_key="delivery.id")
    type: MovementType
    item_id: str = Field(foreign_key="item.id")
    location_id: str = Field(foreign_key="location.id")
    quantity: int
    created_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 4: Implementar `db.py`, `security.py` (hash) e `seed.py`**

Create `backend/app/db.py`:

```python
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def make_engine(url: str):
    kwargs: dict = {"connect_args": {"check_same_thread": False}}
    if url in ("sqlite://", "sqlite:///:memory:"):
        kwargs["poolclass"] = StaticPool  # uma única conexão: o banco em memória vive entre as threads do TestClient
    return create_engine(url, **kwargs)


engine = make_engine(settings.database_url)


def create_db(eng=None) -> None:
    SQLModel.metadata.create_all(eng or engine)


def get_session():
    with Session(engine) as session:
        yield session
```

Create `backend/app/security.py`:

```python
import hashlib
import hmac
import secrets

from app.config import settings


def hash_password(password: str, *, salt: bytes | None = None, iterations: int | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    iterations = iterations or settings.password_iterations
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)
```

Create `backend/app/seed.py`:

```python
import json
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.models import Item, Location, Role, Stock, User
from app.security import hash_password

SEEDS = Path(__file__).resolve().parent.parent / "seeds"

# (username, papel, local padrão). Todos usam GERALDO_DEMO_PASSWORD; só para demonstração.
DEMO_USERS = [
    ("medico1", Role.medico, "consultorio1"),
    ("medico2", Role.medico, "consultorio2"),
    ("enfermeiro1", Role.enfermeiro, "enfermaria214"),
    ("farmaceutico1", Role.farmaceutico, "farmacia"),
    ("admin", Role.admin, None),
    ("robo", Role.robo, None),
]


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed(session: Session, seeds_dir: Path = SEEDS) -> None:
    """Insere o que falta; nunca sobrescreve estoque nem usuários existentes."""
    for loc in _load(seeds_dir / "locais.json"):
        if session.get(Location, loc["id"]) is None:
            session.add(Location(**loc))
    for item in _load(seeds_dir / "itens.json"):
        if session.get(Item, item["id"]) is None:
            session.add(Item(**item))
    session.commit()
    for st in _load(seeds_dir / "estoque.json"):
        if session.get(Stock, (st["location_id"], st["item_id"])) is None:
            session.add(Stock(**st))
    for username, role, local_id in DEMO_USERS:
        if session.exec(select(User).where(User.username == username)).first() is None:
            session.add(User(username=username, password_hash=hash_password(settings.demo_password), role=role, local_id=local_id))
    session.commit()
```

Create `backend/seeds/itens.json`:

```json
[
  {"id": "dipirona-500mg", "name": "Dipirona 500 mg", "unit": "caixa"},
  {"id": "amoxicilina-500mg", "name": "Amoxicilina 500 mg", "unit": "caixa"},
  {"id": "soro-fisiologico-500ml", "name": "Soro fisiológico 500 ml", "unit": "bolsa"},
  {"id": "bolsa-sangue-o-neg", "name": "Bolsa de sangue O negativo", "unit": "bolsa"},
  {"id": "lencol-hospitalar", "name": "Lençol hospitalar", "unit": "unidade"},
  {"id": "luva-procedimento", "name": "Luva de procedimento", "unit": "caixa"}
]
```

Create `backend/seeds/estoque.json` (o banco de sangue começa **abaixo do mínimo** de propósito, para a demo):

```json
[
  {"location_id": "farmacia", "item_id": "dipirona-500mg", "quantity": 420, "minimum": 100},
  {"location_id": "farmacia", "item_id": "amoxicilina-500mg", "quantity": 200, "minimum": 60},
  {"location_id": "farmacia", "item_id": "soro-fisiologico-500ml", "quantity": 300, "minimum": 80},
  {"location_id": "farmacia", "item_id": "luva-procedimento", "quantity": 150, "minimum": 40},
  {"location_id": "banco_sangue", "item_id": "bolsa-sangue-o-neg", "quantity": 6, "minimum": 10},
  {"location_id": "uti", "item_id": "soro-fisiologico-500ml", "quantity": 20, "minimum": 10},
  {"location_id": "consultorio1", "item_id": "luva-procedimento", "quantity": 10, "minimum": 5},
  {"location_id": "consultorio2", "item_id": "luva-procedimento", "quantity": 10, "minimum": 5},
  {"location_id": "enfermaria214", "item_id": "amoxicilina-500mg", "quantity": 12, "minimum": 6},
  {"location_id": "enfermaria215", "item_id": "lencol-hospitalar", "quantity": 30, "minimum": 10}
]
```

(O arquivo `backend/seeds/locais.json` é gerado pelo Samuel com `python tools/gen_hospital.py`; se ainda não existir no seu clone, rode o gerador ou peça o PR.)

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest -q`
Expected: `7 passed` (1 de health, 3 de senha, 3 de seed).

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend
git commit -m "feat(backend): modelos, banco, hash de senha e seed"
```

---

### Task 3: Login, JWT e papéis

**Files:**
- Create: `backend/app/schemas.py`, `backend/app/deps.py`, `backend/app/routers/__init__.py`, `backend/app/routers/auth.py`
- Modify: `backend/app/security.py` (acrescenta os tokens), `backend/app/main.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `User`, `Role`, `get_session`, `settings` (Tarefa 2).
- Produces:
  - `app.security.create_token(user) -> str` e `decode_token(token) -> dict` (levanta `jwt.PyJWTError`).
  - `app.deps.get_current_user` e `app.deps.require_roles(*roles)` (dependências FastAPI; 401 sem token válido, 403 sem papel).
  - `POST /auth/login` e `GET /me`; fixtures de teste `client` e `auth(username) -> {"Authorization": "Bearer ..."}`.

- [ ] **Step 1: Estender o `conftest.py` e escrever os testes (falham primeiro)**

Replace `backend/tests/conftest.py`:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.db import create_db, get_session, make_engine
from app.main import app
from app.seed import seed

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
PASSWORD = "senha-de-teste"


@pytest.fixture(autouse=True)
def test_settings():
    names = ("jwt_secret", "jwt_minutes", "demo_password", "password_iterations", "auto_seed")
    old = {n: getattr(settings, n) for n in names}
    settings.jwt_secret = "segredo-de-teste-com-mais-de-32-bytes-0123456789"
    settings.jwt_minutes = 60
    settings.demo_password = PASSWORD
    settings.password_iterations = 1000
    settings.auto_seed = False
    yield
    for n, v in old.items():
        setattr(settings, n, v)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    create_db(eng)
    with Session(eng) as s:
        seed(s, FIXTURES)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    def login(username: str) -> dict:
        r = client.post("/auth/login", json={"username": username, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return login
```

Create `backend/tests/test_auth.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.security import decode_token
from tests.conftest import PASSWORD


def forge(payload: dict, key: str, algorithm: str) -> dict:
    return {"Authorization": f"Bearer {jwt.encode(payload, key, algorithm=algorithm)}"}


def valid_payload(**over) -> dict:
    base = {
        "sub": "1",
        "role": "medico",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "jti": uuid.uuid4().hex,
    }
    base.update(over)
    return base


def test_login_returns_a_bearer_token_with_the_contract_claims(client):
    r = client.post("/auth/login", json={"username": "medico1", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    claims = decode_token(body["access_token"])
    assert set(claims) >= {"sub", "role", "exp", "jti"}
    assert claims["role"] == "medico"


def test_login_rejects_wrong_password_and_unknown_user(client):
    for body in ({"username": "medico1", "password": "errada"}, {"username": "ninguem", "password": PASSWORD}):
        r = client.post("/auth/login", json=body)
        assert r.status_code == 401
        assert "senha" in r.json()["detail"].lower()


def test_me_returns_role_and_default_location(client, auth):
    r = client.get("/me", headers=auth("medico1"))
    assert r.status_code == 200
    assert r.json() == {"id": r.json()["id"], "username": "medico1", "role": "medico", "local_id": "consultorio1"}


def test_me_without_token_is_401(client):
    assert client.get("/me").status_code == 401


def test_expired_token_is_401(client):
    settings.jwt_minutes = -1
    headers = {"Authorization": "Bearer " + client.post("/auth/login", json={"username": "medico1", "password": PASSWORD}).json()["access_token"]}
    assert client.get("/me", headers=headers).status_code == 401


def test_token_with_none_algorithm_is_rejected(client):
    assert client.get("/me", headers=forge(valid_payload(), "", "none")).status_code == 401


def test_token_signed_with_another_secret_is_rejected(client):
    other = "outro-segredo-com-mais-de-32-bytes-9876543210"
    assert client.get("/me", headers=forge(valid_payload(), other, "HS256")).status_code == 401


def test_token_without_jti_is_rejected(client):
    payload = valid_payload()
    del payload["jti"]
    assert client.get("/me", headers=forge(payload, settings.jwt_secret, "HS256")).status_code == 401


def test_garbage_token_is_401(client):
    assert client.get("/me", headers={"Authorization": "Bearer isto-nao-e-jwt"}).status_code == 401
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_auth.py -q`
Expected: FAIL (`decode_token` e as rotas não existem).

- [ ] **Step 3: Acrescentar os tokens em `security.py`**

Append to `backend/app/security.py` (e acrescente os imports no topo: `import uuid`, `from datetime import datetime, timedelta, timezone`, `import jwt`, `from app.models import User`):

```python
def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Aceita somente HS256 e exige exp, sub, role e jti (docs/contracts/jwt.md)."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"require": ["exp", "sub", "role", "jti"]},
    )
```

- [ ] **Step 4: Implementar schemas, dependências e o router de auth**

Create `backend/app/schemas.py`:

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DeliveryStatus, MovementType, Priority, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: Role
    local_id: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    has_stock: bool
    waypoint: str | None = None


class StockOut(BaseModel):
    location_id: str
    item_id: str
    item_name: str
    quantity: int
    reserved: int
    minimum: int


class DeliveryItemIn(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class DeliveryCreate(BaseModel):
    origin_id: str
    dest_id: str | None = None
    items: list[DeliveryItemIn] = Field(min_length=1)
    priority: Priority


class DeliveryOut(BaseModel):
    id: int
    origin_id: str
    dest_id: str
    items: list[DeliveryItemIn]
    priority: Priority
    status: DeliveryStatus
    requested_by: int
    created_at: datetime


class RobotTaskOut(DeliveryOut):
    origin_waypoint: str
    dest_waypoint: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_id: int | None
    type: MovementType
    item_id: str
    location_id: str
    quantity: int
    created_at: datetime
```

Create `backend/app/deps.py`:

```python
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db import get_session
from app.models import Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    try:
        claims = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre de novo.")
    user = session.get(User, int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre de novo.")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Seu perfil não tem permissão para isso.")
        return user

    return checker
```

Create `backend/app/routers/__init__.py` (vazio) e `backend/app/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginRequest, MeResponse, TokenResponse
from app.security import create_token, verify_password

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.username == body.username)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos. Tente de novo.")
    return TokenResponse(access_token=create_token(user))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=user.id, username=user.username, role=user.role, local_id=user.local_id)
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.routers import auth
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest -q`
Expected: `16 passed`.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend
git commit -m "feat(backend): login JWT (HS256), /me e dependencias de papel"
```

---

### Task 4: Locais, estoque e criação de entrega (Command)

**Files:**
- Create: `backend/app/queries.py`, `backend/app/commands/__init__.py`, `backend/app/commands/create_delivery.py`, `backend/app/routers/catalog.py`, `backend/app/routers/deliveries.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_catalog.py`, `backend/tests/test_deliveries.py`

**Interfaces:**
- Consumes: `get_current_user`, `require_roles`, modelos, schemas (Tarefas 2 e 3).
- Produces:
  - `app.commands.create_delivery.CreateDelivery(session, user, payload).execute() -> Delivery` e as exceções `DeliveryError` (com `.status_code`), `UnknownLocation`, `UnknownItem`, `SameLocation`, `InsufficientStock`.
  - `app.queries.delivery_out(session, delivery) -> DeliveryOut`.
  - `GET /locations`, `GET /stock`, `POST /deliveries`, `GET /deliveries`, `GET /deliveries/{id}`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Create `backend/tests/test_catalog.py`:

```python
def test_locations_require_login(client):
    assert client.get("/locations").status_code == 401


def test_locations_list_includes_waypoints(client, auth):
    r = client.get("/locations", headers=auth("medico1"))
    assert r.status_code == 200
    by_id = {l["id"]: l for l in r.json()}
    assert by_id["farmacia"]["waypoint"] == "farmacia_balcao"
    assert by_id["recepcao"]["waypoint"] is None
    assert by_id["recepcao"]["has_stock"] is False


def test_stock_can_be_filtered_by_location(client, auth):
    r = client.get("/stock", params={"location_id": "farmacia"}, headers=auth("medico1"))
    assert r.status_code == 200
    assert r.json() == [
        {"location_id": "farmacia", "item_id": "dipirona-500mg", "item_name": "Dipirona 500 mg", "quantity": 420, "reserved": 0, "minimum": 100}
    ]
    assert len(client.get("/stock", headers=auth("medico1")).json()) == 3
```

Create `backend/tests/test_deliveries.py`:

```python
from sqlmodel import select

from app.models import Movement, MovementType


def payload(**over) -> dict:
    base = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}
    base.update(over)
    return base


def farmacia_stock(client, auth) -> dict:
    return client.get("/stock", params={"location_id": "farmacia"}, headers=auth("medico1")).json()[0]


def test_destination_defaults_to_the_users_location(client, auth):
    r = client.post("/deliveries", json=payload(), headers=auth("medico1"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["dest_id"] == "consultorio1"
    assert body["status"] == "NA_FILA"
    assert body["items"] == [{"item_id": "dipirona-500mg", "quantity": 10}]


def test_explicit_destination_is_respected(client, auth):
    r = client.post("/deliveries", json=payload(dest_id="enfermaria214"), headers=auth("medico1"))
    assert r.status_code == 201 and r.json()["dest_id"] == "enfermaria214"


def test_creating_reserves_stock_and_logs_a_movement(client, auth, session):
    client.post("/deliveries", json=payload(), headers=auth("medico1"))
    stock = farmacia_stock(client, auth)
    assert (stock["quantity"], stock["reserved"]) == (420, 10)
    moves = session.exec(select(Movement)).all()
    assert len(moves) == 1
    assert (moves[0].type, moves[0].item_id, moves[0].location_id, moves[0].quantity) == (
        MovementType.RESERVA, "dipirona-500mg", "farmacia", 10,
    )


def test_duplicate_items_are_summed(client, auth):
    items = [{"item_id": "dipirona-500mg", "quantity": 5}, {"item_id": "dipirona-500mg", "quantity": 7}]
    r = client.post("/deliveries", json=payload(items=items), headers=auth("medico1"))
    assert r.status_code == 201
    assert r.json()["items"] == [{"item_id": "dipirona-500mg", "quantity": 12}]
    assert farmacia_stock(client, auth)["reserved"] == 12


def test_critical_delivery_waits_for_the_pharmacists_approval(client, auth):
    body = payload(origin_id="banco_sangue", items=[{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], priority="critica")
    r = client.post("/deliveries", json=body, headers=auth("medico1"))
    assert r.status_code == 201 and r.json()["status"] == "PENDENTE_APROVACAO"


def test_insufficient_stock_is_409_and_reserves_nothing(client, auth):
    items = [{"item_id": "dipirona-500mg", "quantity": 1000}]
    r = client.post("/deliveries", json=payload(items=items), headers=auth("medico1"))
    assert r.status_code == 409
    assert "Estoque insuficiente" in r.json()["detail"]
    assert farmacia_stock(client, auth)["reserved"] == 0


def test_reservations_count_against_the_available_balance(client, auth):
    items = [{"item_id": "dipirona-500mg", "quantity": 400}]
    assert client.post("/deliveries", json=payload(items=items), headers=auth("medico1")).status_code == 201
    r = client.post("/deliveries", json=payload(items=[{"item_id": "dipirona-500mg", "quantity": 30}]), headers=auth("medico2"))
    assert r.status_code == 409


def test_invalid_requests_are_422(client, auth):
    h = auth("medico1")
    assert client.post("/deliveries", json=payload(origin_id="narnia"), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(dest_id="recepcao"), headers=h).status_code == 422   # sem waypoint
    assert client.post("/deliveries", json=payload(dest_id="farmacia"), headers=h).status_code == 422   # origem = destino
    assert client.post("/deliveries", json=payload(items=[{"item_id": "cura-de-tudo", "quantity": 1}]), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(items=[]), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(items=[{"item_id": "dipirona-500mg", "quantity": 0}]), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(priority="urgentissima"), headers=h).status_code == 422


def test_user_without_default_location_must_inform_the_destination(client, auth):
    r = client.post("/deliveries", json=payload(), headers=auth("admin"))
    assert r.status_code == 422 and "destino" in r.json()["detail"].lower()


def test_roles_and_authentication(client, auth):
    assert client.post("/deliveries", json=payload()).status_code == 401
    assert client.post("/deliveries", json=payload(), headers=auth("robo")).status_code == 403


def test_list_shows_own_deliveries_to_doctors_and_all_to_the_pharmacist(client, auth):
    client.post("/deliveries", json=payload(), headers=auth("medico1"))
    client.post("/deliveries", json=payload(), headers=auth("medico2"))
    assert len(client.get("/deliveries", headers=auth("medico1")).json()) == 1
    assert len(client.get("/deliveries", headers=auth("farmaceutico1")).json()) == 2
    assert len(client.get("/deliveries", headers=auth("admin")).json()) == 2


def test_get_delivery_of_someone_else_is_404(client, auth):
    delivery_id = client.post("/deliveries", json=payload(), headers=auth("medico1")).json()["id"]
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).status_code == 200
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("farmaceutico1")).status_code == 200
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico2")).status_code == 404
    assert client.get("/deliveries/9999", headers=auth("medico1")).status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_catalog.py tests/test_deliveries.py -q`
Expected: FAIL (rotas não existem).

- [ ] **Step 3: Implementar `queries.py` e o comando `CreateDelivery`**

Create `backend/app/queries.py`:

```python
from sqlmodel import Session, select

from app.models import Delivery, DeliveryItem
from app.schemas import DeliveryItemIn, DeliveryOut


def delivery_out(session: Session, delivery: Delivery) -> DeliveryOut:
    items = session.exec(select(DeliveryItem).where(DeliveryItem.delivery_id == delivery.id).order_by(DeliveryItem.id)).all()
    return DeliveryOut(
        id=delivery.id,
        origin_id=delivery.origin_id,
        dest_id=delivery.dest_id,
        items=[DeliveryItemIn(item_id=i.item_id, quantity=i.quantity) for i in items],
        priority=delivery.priority,
        status=delivery.status,
        requested_by=delivery.requested_by,
        created_at=delivery.created_at,
    )
```

Create `backend/app/commands/__init__.py` (vazio) e `backend/app/commands/create_delivery.py`:

```python
from sqlmodel import Session

from app.models import (
    Delivery,
    DeliveryItem,
    DeliveryStatus,
    Item,
    Location,
    Movement,
    MovementType,
    Priority,
    Stock,
    User,
)
from app.schemas import DeliveryCreate


class DeliveryError(Exception):
    status_code = 400


class UnknownLocation(DeliveryError):
    status_code = 422


class UnknownItem(DeliveryError):
    status_code = 422


class SameLocation(DeliveryError):
    status_code = 422


class InsufficientStock(DeliveryError):
    status_code = 409


class CreateDelivery:
    """Comando CriarEntrega: valida, reserva o estoque na origem e registra a movimentação."""

    def __init__(self, session: Session, user: User, payload: DeliveryCreate) -> None:
        self.session = session
        self.user = user
        self.payload = payload

    def execute(self) -> Delivery:
        session, payload = self.session, self.payload
        dest_id = payload.dest_id or self.user.local_id
        if dest_id is None:
            raise UnknownLocation("Informe o destino: seu usuário não tem um local padrão.")
        for loc_id in (payload.origin_id, dest_id):
            location = session.get(Location, loc_id)
            if location is None:
                raise UnknownLocation(f"Local desconhecido: {loc_id}. Escolha um local da lista.")
            if location.waypoint is None:
                raise UnknownLocation(f"O local {location.name} não recebe entregas do robô. Escolha outro.")
        if payload.origin_id == dest_id:
            raise SameLocation("Origem e destino são o mesmo local. Escolha destinos diferentes.")

        wanted: dict[str, int] = {}
        for line in payload.items:
            wanted[line.item_id] = wanted.get(line.item_id, 0) + line.quantity

        stocks: dict[str, Stock] = {}
        for item_id, qty in wanted.items():
            if session.get(Item, item_id) is None:
                raise UnknownItem(f"Item desconhecido: {item_id}. Escolha um item da lista.")
            stock = session.get(Stock, (payload.origin_id, item_id))
            available = 0 if stock is None else stock.quantity - stock.reserved
            if available < qty:
                raise InsufficientStock(
                    f"Estoque insuficiente de {item_id} em {payload.origin_id}: disponível {available}, pedido {qty}. Reduza a quantidade."
                )
            stocks[item_id] = stock

        status = DeliveryStatus.PENDENTE_APROVACAO if payload.priority == Priority.critica else DeliveryStatus.NA_FILA
        delivery = Delivery(
            origin_id=payload.origin_id,
            dest_id=dest_id,
            priority=payload.priority,
            status=status,
            requested_by=self.user.id,
        )
        session.add(delivery)
        session.flush()
        for item_id, qty in wanted.items():
            session.add(DeliveryItem(delivery_id=delivery.id, item_id=item_id, quantity=qty))
            stocks[item_id].reserved += qty
            session.add(stocks[item_id])
            session.add(
                Movement(
                    delivery_id=delivery.id,
                    type=MovementType.RESERVA,
                    item_id=item_id,
                    location_id=payload.origin_id,
                    quantity=qty,
                )
            )
        session.commit()
        session.refresh(delivery)
        return delivery
```

- [ ] **Step 4: Implementar os routers e ligar no `main.py`**

Create `backend/app/routers/catalog.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user
from app.models import Item, Location, Stock, User
from app.schemas import LocationOut, StockOut

router = APIRouter()


@router.get("/locations", response_model=list[LocationOut])
def locations(_: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Location).order_by(Location.id)).all()


@router.get("/stock", response_model=list[StockOut])
def stock(location_id: str | None = None, _: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(Stock, Item).join(Item, Item.id == Stock.item_id).order_by(Stock.location_id, Stock.item_id)
    if location_id:
        query = query.where(Stock.location_id == location_id)
    return [
        StockOut(location_id=s.location_id, item_id=s.item_id, item_name=i.name, quantity=s.quantity, reserved=s.reserved, minimum=s.minimum)
        for s, i in session.exec(query).all()
    ]
```

Create `backend/app/routers/deliveries.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.commands.create_delivery import CreateDelivery, DeliveryError
from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models import Delivery, Role, User
from app.queries import delivery_out
from app.schemas import DeliveryCreate, DeliveryOut

router = APIRouter()
SEE_ALL = (Role.admin, Role.farmaceutico)


@router.post("/deliveries", response_model=DeliveryOut, status_code=201)
def create_delivery(
    body: DeliveryCreate,
    user: User = Depends(require_roles(Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)),
    session: Session = Depends(get_session),
) -> DeliveryOut:
    try:
        delivery = CreateDelivery(session, user, body).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.get("/deliveries", response_model=list[DeliveryOut])
def list_deliveries(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(Delivery).order_by(Delivery.id)
    if user.role not in SEE_ALL:
        query = query.where(Delivery.requested_by == user.id)
    return [delivery_out(session, d) for d in session.exec(query).all()]


@router.get("/deliveries/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    delivery = session.get(Delivery, delivery_id)
    if delivery is None or (user.role not in SEE_ALL and delivery.requested_by != user.id):
        raise HTTPException(status_code=404, detail="Entrega não encontrada.")
    return delivery_out(session, delivery)
```

Edit `backend/app/main.py`: troque `from app.routers import auth` por `from app.routers import auth, catalog, deliveries` e, depois de `app.include_router(auth.router)`, acrescente:

```python
app.include_router(catalog.router)
app.include_router(deliveries.router)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest -q`
Expected: todos passam (`16` anteriores + `3` de catálogo + `12` de entregas = `31 passed`).

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend
git commit -m "feat(backend): locais, estoque e criacao de entrega com reserva (Command)"
```

---

### Task 5: Fila de prioridade e `/robot/next-task`

**Files:**
- Create: `backend/app/routers/robot.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_robot_queue.py`

**Interfaces:**
- Consumes: `require_roles`, `delivery_out`, modelos (Tarefas 2 a 4).
- Produces: `POST /robot/next-task` (papel `robo`): `200` com `RobotTask` (entrega + `origin_waypoint` e `dest_waypoint`), a entrega passa a `EM_ROTA`; `204` se a fila (apenas `NA_FILA`) estiver vazia. Ordem: `critica` < `media` < `rotina`, depois `id`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Create `backend/tests/test_robot_queue.py`:

```python
def make(client, auth, user, priority, **over):
    body = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": priority}
    body.update(over)
    r = client.post("/deliveries", json=body, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def next_task(client, auth):
    return client.post("/robot/next-task", headers=auth("robo"))


def test_media_goes_before_rotina_and_fifo_within_the_same_priority(client, auth):
    rotina = make(client, auth, "medico1", "rotina")
    media_a = make(client, auth, "medico1", "media")
    media_b = make(client, auth, "medico2", "media")
    order = [next_task(client, auth).json()["id"] for _ in range(3)]
    assert order == [media_a, media_b, rotina]
    assert next_task(client, auth).status_code == 204


def test_dispatched_delivery_becomes_em_rota(client, auth):
    delivery_id = make(client, auth, "medico1", "media")
    task = next_task(client, auth)
    assert task.status_code == 200
    assert task.json()["status"] == "EM_ROTA"
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"] == "EM_ROTA"


def test_task_carries_the_waypoints_of_origin_and_destination(client, auth):
    make(client, auth, "medico1", "media")
    body = next_task(client, auth).json()
    assert body["origin_waypoint"] == "farmacia_balcao"
    assert body["dest_waypoint"] == "cons1_entrega"
    assert body["items"] == [{"item_id": "dipirona-500mg", "quantity": 1}]


def test_critical_is_not_dispatched_until_approved(client, auth):
    make(client, auth, "medico1", "critica", origin_id="banco_sangue", items=[{"item_id": "bolsa-sangue-o-neg", "quantity": 1}])
    assert next_task(client, auth).status_code == 204


def test_only_the_robot_can_ask_for_tasks(client, auth):
    assert client.post("/robot/next-task").status_code == 401
    assert client.post("/robot/next-task", headers=auth("medico1")).status_code == 403
    assert client.post("/robot/next-task", headers=auth("admin")).status_code == 403
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_robot_queue.py -q`
Expected: FAIL (rota não existe).

- [ ] **Step 3: Implementar o router**

Create `backend/app/routers/robot.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_roles
from app.models import Delivery, DeliveryStatus, Location, Priority, Role, User
from app.queries import delivery_out
from app.schemas import RobotTaskOut

router = APIRouter()
PRIORITY_RANK = {Priority.critica: 0, Priority.media: 1, Priority.rotina: 2}


@router.post("/robot/next-task", response_model=RobotTaskOut, responses={204: {"description": "Fila vazia"}})
def next_task(_: User = Depends(require_roles(Role.robo)), session: Session = Depends(get_session)):
    queued = session.exec(select(Delivery).where(Delivery.status == DeliveryStatus.NA_FILA)).all()
    if not queued:
        return Response(status_code=204)
    delivery = min(queued, key=lambda d: (PRIORITY_RANK[d.priority], d.id))
    origin, dest = session.get(Location, delivery.origin_id), session.get(Location, delivery.dest_id)
    if origin is None or dest is None or origin.waypoint is None or dest.waypoint is None:
        raise HTTPException(status_code=409, detail="A entrega aponta para um local sem ponto de parada. Corrija os locais.")
    delivery.status = DeliveryStatus.EM_ROTA
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return RobotTaskOut(**delivery_out(session, delivery).model_dump(), origin_waypoint=origin.waypoint, dest_waypoint=dest.waypoint)
```

Edit `backend/app/main.py`: `from app.routers import auth, catalog, deliveries, robot` e `app.include_router(robot.router)`.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest -q`
Expected: `36 passed`.

- [ ] **Step 5: Rodar o servidor e conferir à mão**

```bash
export GERALDO_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export GERALDO_DEMO_PASSWORD="demo-local"
uvicorn app.main:app --reload
```

Em outro terminal:

```bash
TOKEN=$(curl -s localhost:8000/auth/login -H 'content-type: application/json' -d '{"username":"medico1","password":"demo-local"}' | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s localhost:8000/me -H "authorization: Bearer $TOKEN"
curl -s localhost:8000/deliveries -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"origin_id":"farmacia","items":[{"item_id":"dipirona-500mg","quantity":5}],"priority":"media"}'
```

Expected: `/me` mostra `medico1` com `local_id: "consultorio1"`; o `POST /deliveries` devolve `201` com `status: "NA_FILA"`. Documentação interativa em `http://localhost:8000/docs`.

- [ ] **Step 6: Commit e PR**

```bash
cd ..
git add backend
git commit -m "feat(backend): fila de prioridade e /robot/next-task"
git push -u origin HEAD
```

Abra o PR e avise o Pedro: o teste de contrato (`backend/tests/test_contract.py`) já pode rodar com as rotas da semana 1; as ainda pendentes (`cancel`, `approve`, `confirm-receipt`, `movements`, `robot/events`, `telemetry`) entram nas semanas 2 e 3.
