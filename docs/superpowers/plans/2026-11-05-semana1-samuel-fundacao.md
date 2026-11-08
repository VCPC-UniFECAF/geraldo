# G.E.R.A.L.D.O. — Semana 1 (Samuel): fundação, contratos, hospital e tokens

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deixar o repositório pronto para as 4 pessoas trabalharem em paralelo: estrutura de pastas, modelo 3D no repo, guia das IAs, contratos da API e do ROS, o hospital gerado de um único YAML e os tokens do design system.

**Architecture:** Tudo que é compartilhado vive em arquivos versionados com fonte única: `docs/contracts/` (contratos), `hospital/hospital.yaml` (planta; um script gera mundo do Gazebo, mapa do Nav2, locais do backend e waypoints) e `design-system/tokens/tokens.json` (um script gera CSS, preset do Tailwind e cores do Unity). Os geradores têm testes automáticos.

**Tech Stack:** Python 3.11+ (pytest, PyYAML, numpy), Node 20+ (`node:test`, sem dependências), Markdown e YAML.

**Spec:** `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` e `docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md`

## Global Constraints

- Documentos em português; comandos, nomes de pastas e código em inglês (spec §9).
- Unidades em metros; origem do hospital no canto sudoeste; x para leste, y para norte (spec §3).
- Hospital de 46 × 30 m; corredores de 2,0 m; portas de 1,0 m (spec §3).
- Footprint do robô de 0,70 × 0,50 m com 10 cm de inflação (spec §4.1).
- Contratos em `docs/contracts/` travados até domingo, 08/11/2026 (spec §6).
- Nenhum hex de cor fora de `design-system/tokens/tokens.json` e `design-system/dist/` (DS §2).
- Nenhum segredo no repositório (spec §9).
- Padrões de código (`docs/padroes-de-projeto.md`, adicionado em 08/11): `tools/gen_hospital.py` é feito de **funções puras** (`wall_segments`, `rasterize`, `inflate`, `distances`) e cada `write_*` escreve um arquivo só; `generate()` é o único ponto que junta tudo (SRP). Nenhuma função lê estado global.
- Branch `feat/<frente>-<assunto>`; commits em português, curtos; nada direto na `main`.

---

### Task 1: Estrutura do repositório e modelo 3D

> **Já feito em 05/11/2026 (direto na `main`):** a pasta `modelos-3d/` com `geraldoV1.blend`, `geraldoV1.glb`, `build_geraldoV1.py` e `renders/`, o `README.md` da raiz e a imagem `docs/img/planta-hospital.png`. Os passos de copiar o modelo e de escrever os READMEs abaixo **não precisam ser repetidos**; falta criar as pastas vazias e o `.gitignore`. O teste de estrutura continua valendo.

**Files:**
- Create: `.gitignore`, `README.md` (substitui o atual), `modelos-3d/README.md`
- Create (copiados): `modelos-3d/geraldoV1.blend`, `modelos-3d/geraldoV1.glb`, `modelos-3d/build_geraldoV1.py`, `modelos-3d/renders/*.png`
- Create (vazios): `backend/.gitkeep`, `web/.gitkeep`, `security/.gitkeep`, `unity/.gitkeep`, `ros2_ws/src/.gitkeep`, `design-system/.gitkeep`, `hospital/.gitkeep`, `tools/.gitkeep`

**Interfaces:**
- Consumes: o modelo já em `modelos-3d/` (`geraldoV1.blend`, `geraldoV1.glb`, `build_geraldoV1.py`, `renders/geraldoV1_<vista>.png`).
- Produces: a estrutura de pastas da spec §12 e do `AGENTS.md`; o modelo em `modelos-3d/` (usado na Tarefa 3 do plano do robô).

- [ ] **Step 1: Criar a branch a partir da branch das specs**

```bash
cd /home/samuel/projects/fecaf/geraldo
git checkout docs/plano-desenvolvimento
git checkout -b feat/samuel-fundacao
```

- [ ] **Step 2: Escrever o teste de estrutura (falha primeiro)**

Create `tools/tests/test_repo_layout.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    "modelos-3d",
    "backend",
    "web",
    "security",
    "unity",
    "ros2_ws/src",
    "design-system",
    "hospital",
    "tools",
    "docs/contracts",
    "docs/prompts",
]

REQUIRED_FILES = [
    "README.md",
    ".gitignore",
    "modelos-3d/geraldoV1.blend",
    "modelos-3d/geraldoV1.glb",
    "modelos-3d/build_geraldoV1.py",
]


def test_required_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"pastas faltando: {missing}"


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"arquivos faltando: {missing}"


def test_model_files_are_not_empty():
    for name in ("geraldoV1.blend", "geraldoV1.glb"):
        assert (ROOT / "modelos-3d" / name).stat().st_size > 100_000, name


def test_renders_were_copied():
    renders = list((ROOT / "modelos-3d/renders").glob("*.png"))
    assert len(renders) >= 6
```

Create `tools/__init__.py` (arquivo vazio) e `tools/tests/__init__.py` (arquivo vazio).

- [ ] **Step 3: Rodar o teste e ver falhar**

Run: `python -m pytest tools/tests/test_repo_layout.py -q`
Expected: FAIL (pastas e arquivos faltando).

- [ ] **Step 4: Criar as pastas vazias e escrever `.gitignore`**

```bash
cd /home/samuel/projects/fecaf/geraldo
for d in backend web security unity ros2_ws/src design-system hospital tools docs/contracts docs/prompts modelos-3d/renders; do mkdir -p "$d"; done
for d in backend web security unity ros2_ws/src design-system hospital; do touch "$d/.gitkeep"; done
ls modelos-3d modelos-3d/renders   # o modelo já está aqui
```

Create `.gitignore`:

```gitignore
__pycache__/
.pytest_cache/
.venv/
node_modules/
web/dist/
*.blend1
.env
*.db
build/
install/
log/
```

(`design-system/dist/` **não** é ignorado: os arquivos gerados são versionados.)

- [ ] **Step 5: Escrever `modelos-3d/README.md` e o `README.md` da raiz**

Create `modelos-3d/README.md`:

```markdown
# Modelo 3D do G.E.R.A.L.D.O.

| Arquivo | Para quê |
|---|---|
| `geraldoV1.blend` | Cena editável do Blender (robô, cenário, 6 câmeras) |
| `geraldoV1.glb` | Só o robô, para o Unity e para a web |
| `build_geraldoV1.py` | Script que gera tudo. Rode com `blender -b --python build_geraldoV1.py` |
| `renders/` | Imagens de referência (vistas hero, frente, traseira, lateral, aérea, topo) |

Dimensões: chassi 0,70 × 0,50 m; rodas de tração de 0,20 m de diâmetro (eixo em x = +0,10 m, separação de 0,45 m); rodízio traseiro de 0,08 m; baú de 0,48 × 0,40 m; altura total de 0,47 m. Frente do robô = +X; eixo das rodas = Y; `base_link` no chão.

O Gazebo **não** usa o `.blend`: usa a malha exportada pelo script `tools/export_blender_mesh.py` (ver o plano do robô).
```

Create `README.md`:

```markdown
# G.E.R.A.L.D.O.

**G**estor de **E**ntregas e **R**eposição **A**utônoma para **L**eitos e **D**ispensação **O**timizada.

Robô hospitalar autônomo, simulado no Gazebo, que leva medicamentos e insumos da farmácia e do banco de sangue até consultórios, enfermarias, UTI, centro cirúrgico e pronto-socorro, e atualiza o estoque do hospital conforme transporta. Projeto da ExpoTech (28/11/2026).

## Comece por aqui

1. Leia o [`AGENTS.md`](AGENTS.md): regras, mapa de pastas e como rodar.
2. Leia a [spec do plano](docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md) e o [plano da semana 1](docs/superpowers/plans/README.md).
3. Pegue o seu plano em `docs/superpowers/plans/` e o seu prompt de partida em `docs/prompts/`.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `modelos-3d/` | Modelo 3D do robô |
| `hospital/` | `hospital.yaml`: a planta do hospital (fonte única) |
| `ros2_ws/` | Robô, simulação, Nav2 e `geraldo_dispatcher` |
| `backend/` | API FastAPI, estoque e gestão hospitalar |
| `web/` | Sistema web responsivo para os profissionais |
| `design-system/` | Tokens, componentes e guia visual |
| `security/` | Ataques de teste e relatório do pentest |
| `unity/` | Cockpit 3D (extra) |
| `docs/` | Specs, planos, contratos e prompts |
| `tools/` | Geradores e utilitários |

## Equipe

Samuel (líder: robô, simulação, hospital) · Erik (backend) · Vieira (web) · Pedro (qualidade e segurança)
```

- [ ] **Step 6: Rodar o teste e ver passar**

Run: `python -m pytest tools/tests/test_repo_layout.py -q`
Expected: `4 passed`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: estrutura do repositorio e modelo 3D"
```

---

### Task 2: Contratos da API e do ROS (travar até domingo)

**Files:**
- Create: `docs/contracts/openapi.yaml`, `docs/contracts/ros-interfaces.md`, `docs/contracts/jwt.md`
- Test: `tools/tests/test_contracts.py`

**Interfaces:**
- Consumes: spec §6 (rotas, papéis, JWT).
- Produces: o contrato que Erik implementa, Vieira consome, Pedro testa e o `geraldo_dispatcher` usa. Nomes exatos: ids de locais (`farmacia`, `banco_sangue`, `apoio`, `centro_cirurgico`, `uti`, `pronto_socorro`, `recepcao`, `consultorio1`, `consultorio2`, `enfermaria214`, `enfermaria215`), prioridades (`critica`, `media`, `rotina`), status e tipos de movimentação.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_contracts.py`:

```python
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/contracts/openapi.yaml"

EXPECTED_OPERATIONS = {
    ("post", "/auth/login"),
    ("get", "/me"),
    ("get", "/locations"),
    ("get", "/stock"),
    ("post", "/deliveries"),
    ("get", "/deliveries"),
    ("get", "/deliveries/{id}"),
    ("post", "/deliveries/{id}/cancel"),
    ("post", "/deliveries/{id}/approve"),
    ("post", "/deliveries/{id}/confirm-receipt"),
    ("get", "/movements"),
    ("post", "/robot/next-task"),
    ("post", "/robot/events"),
    ("get", "/telemetry"),
}


def load():
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def test_all_contract_operations_are_declared():
    paths = load()["paths"]
    declared = {(m, p) for p, ops in paths.items() for m in ops if m in {"get", "post", "put", "delete"}}
    assert declared == EXPECTED_OPERATIONS


def test_priority_enum_matches_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["Priority"]["enum"] == ["critica", "media", "rotina"]


def test_delivery_status_enum_matches_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["DeliveryStatus"]["enum"] == [
        "PENDENTE_APROVACAO",
        "NA_FILA",
        "EM_ROTA",
        "AGUARDANDO_RECEBIMENTO",
        "ENTREGUE",
        "CANCELADA",
        "FALHOU",
    ]


def test_movement_types_match_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["MovementType"]["enum"] == ["RESERVA", "BAIXA", "CREDITO", "ESTORNO"]


def test_roles_match_spec():
    schemas = load()["components"]["schemas"]
    assert schemas["Role"]["enum"] == ["medico", "enfermeiro", "farmaceutico", "admin", "robo"]


def test_login_is_the_only_public_operation():
    paths = load()["paths"]
    public = [p for p, ops in paths.items() for op in ops.values() if isinstance(op, dict) and op.get("security") == []]
    assert public == ["/auth/login"]


def test_ros_and_jwt_docs_exist():
    for name in ("ros-interfaces.md", "jwt.md"):
        assert (ROOT / "docs/contracts" / name).stat().st_size > 500, name
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pip install pyyaml pytest openapi-spec-validator && python -m pytest tools/tests/test_contracts.py -q`
Expected: FAIL (`openapi.yaml` não existe).

- [ ] **Step 3: Escrever `docs/contracts/openapi.yaml`**

```yaml
openapi: 3.0.3
info:
  title: G.E.R.A.L.D.O. API
  version: 0.1.0
  description: >
    Contrato entre backend (Erik), sistema web (Vieira), robô (geraldo_dispatcher, Samuel),
    Pentest (Pedro) e Unity. Mudança só por PR com aviso ao dono da frente afetada.
    A telemetria em tempo real também existe como WebSocket em /ws/telemetry (mesmo corpo de Telemetry).
servers:
  - url: http://localhost:8000
security:
  - bearerAuth: []
paths:
  /auth/login:
    post:
      summary: Emite o JWT
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LoginRequest' }
      responses:
        '200':
          description: Token emitido
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TokenResponse' }
        '401': { $ref: '#/components/responses/Unauthorized' }
  /me:
    get:
      summary: Usuário logado, papel e local padrão (destino padrão dos pedidos)
      responses:
        '200':
          description: Usuário
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Me' }
        '401': { $ref: '#/components/responses/Unauthorized' }
  /locations:
    get:
      summary: Locais do hospital (vêm do hospital.yaml)
      responses:
        '200':
          description: Lista de locais
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/Location' }
        '401': { $ref: '#/components/responses/Unauthorized' }
  /stock:
    get:
      summary: Saldos de estoque
      parameters:
        - name: location_id
          in: query
          required: false
          schema: { type: string }
      responses:
        '200':
          description: Saldos
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/StockEntry' }
        '401': { $ref: '#/components/responses/Unauthorized' }
  /deliveries:
    post:
      summary: Cria uma entrega (reserva o estoque na origem)
      description: Papéis medico, enfermeiro, farmaceutico e admin. Se dest_id for omitido, usa o local_id do usuário. Prioridade critica fica em PENDENTE_APROVACAO.
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DeliveryCreate' }
      responses:
        '201':
          description: Entrega criada
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '409': { $ref: '#/components/responses/Conflict' }
        '422': { $ref: '#/components/responses/Invalid' }
    get:
      summary: Lista entregas (admin e farmacêutico veem todas; os demais, só as suas)
      responses:
        '200':
          description: Entregas
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
  /deliveries/{id}:
    get:
      summary: Consulta uma entrega
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: Entrega
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '404': { $ref: '#/components/responses/NotFound' }
  /deliveries/{id}/cancel:
    post:
      summary: Cancela e estorna a reserva (solicitante ou admin)
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: Entrega cancelada
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '404': { $ref: '#/components/responses/NotFound' }
        '409': { $ref: '#/components/responses/Conflict' }
  /deliveries/{id}/approve:
    post:
      summary: Assinatura dupla da prioridade crítica (farmacêutico)
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: Entrega aprovada e na fila
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '404': { $ref: '#/components/responses/NotFound' }
        '409': { $ref: '#/components/responses/Conflict' }
  /deliveries/{id}/confirm-receipt:
    post:
      summary: Solicitante confirma o recebimento; libera a tampa e credita o destino
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: Entrega concluída
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '404': { $ref: '#/components/responses/NotFound' }
        '409': { $ref: '#/components/responses/Conflict' }
  /movements:
    get:
      summary: Histórico de movimentações de estoque
      parameters:
        - { name: delivery_id, in: query, required: false, schema: { type: integer } }
        - { name: location_id, in: query, required: false, schema: { type: string } }
      responses:
        '200':
          description: Movimentações
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/Movement' }
        '401': { $ref: '#/components/responses/Unauthorized' }
  /robot/next-task:
    post:
      summary: O dispatcher pede a próxima entrega (maior prioridade, depois FIFO) e ela vira EM_ROTA
      description: Papel robo. Responde 204 se a fila estiver vazia.
      responses:
        '200':
          description: Tarefa
          content:
            application/json:
              schema: { $ref: '#/components/schemas/RobotTask' }
        '204': { description: Fila vazia }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
  /robot/events:
    post:
      summary: Evento do robô (carga trancada, chegada, tampa liberada, falha)
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/RobotEvent' }
      responses:
        '200':
          description: Entrega atualizada
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Delivery' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '404': { $ref: '#/components/responses/NotFound' }
        '409': { $ref: '#/components/responses/Conflict' }
  /telemetry:
    get:
      summary: Último estado do robô (o mesmo corpo sai no WebSocket /ws/telemetry)
      responses:
        '200':
          description: Telemetria
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Telemetry' }
        '401': { $ref: '#/components/responses/Unauthorized' }
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  responses:
    Unauthorized:
      description: Sem login ou token inválido/expirado
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }
    Forbidden:
      description: Papel sem permissão
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }
    NotFound:
      description: Não encontrado
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }
    Conflict:
      description: Estado ou estoque incompatível com a operação
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }
    Invalid:
      description: Corpo inválido
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }
  schemas:
    Error:
      type: object
      required: [detail]
      properties:
        detail: { type: string }
    Role:
      type: string
      enum: [medico, enfermeiro, farmaceutico, admin, robo]
    Priority:
      type: string
      enum: [critica, media, rotina]
    DeliveryStatus:
      type: string
      enum: [PENDENTE_APROVACAO, NA_FILA, EM_ROTA, AGUARDANDO_RECEBIMENTO, ENTREGUE, CANCELADA, FALHOU]
    MovementType:
      type: string
      description: A direção do efeito vem do tipo; quantity é sempre positiva.
      enum: [RESERVA, BAIXA, CREDITO, ESTORNO]
    LoginRequest:
      type: object
      required: [username, password]
      properties:
        username: { type: string }
        password: { type: string }
    TokenResponse:
      type: object
      required: [access_token, token_type]
      properties:
        access_token: { type: string }
        token_type: { type: string, enum: [bearer] }
    Me:
      type: object
      required: [id, username, role]
      properties:
        id: { type: integer }
        username: { type: string }
        role: { $ref: '#/components/schemas/Role' }
        local_id: { type: string, nullable: true }
    Location:
      type: object
      required: [id, name, kind, has_stock]
      properties:
        id: { type: string, example: farmacia }
        name: { type: string, example: Farmácia central }
        kind: { type: string, example: pharmacy }
        has_stock: { type: boolean }
        waypoint: { type: string, nullable: true, description: Ponto de parada do robô neste local (id em waypoints.yaml) }
    StockEntry:
      type: object
      required: [location_id, item_id, item_name, quantity, reserved, minimum]
      properties:
        location_id: { type: string }
        item_id: { type: string }
        item_name: { type: string, example: Dipirona 500 mg }
        quantity: { type: integer, minimum: 0 }
        reserved: { type: integer, minimum: 0 }
        minimum: { type: integer, minimum: 0 }
    DeliveryItem:
      type: object
      required: [item_id, quantity]
      properties:
        item_id: { type: string, example: dipirona-500mg }
        quantity: { type: integer, minimum: 1 }
    DeliveryCreate:
      type: object
      required: [origin_id, items, priority]
      properties:
        origin_id: { type: string }
        dest_id: { type: string, nullable: true, description: "Se omitido, usa o local_id do usuário" }
        items:
          type: array
          minItems: 1
          items: { $ref: '#/components/schemas/DeliveryItem' }
        priority: { $ref: '#/components/schemas/Priority' }
    Delivery:
      type: object
      required: [id, origin_id, dest_id, items, priority, status, requested_by, created_at]
      properties:
        id: { type: integer }
        origin_id: { type: string }
        dest_id: { type: string }
        items:
          type: array
          items: { $ref: '#/components/schemas/DeliveryItem' }
        priority: { $ref: '#/components/schemas/Priority' }
        status: { $ref: '#/components/schemas/DeliveryStatus' }
        requested_by: { type: integer }
        created_at: { type: string, format: date-time }
    RobotTask:
      allOf:
        - $ref: '#/components/schemas/Delivery'
        - type: object
          required: [origin_waypoint, dest_waypoint]
          properties:
            origin_waypoint: { type: string, example: farmacia_balcao }
            dest_waypoint: { type: string, example: cons1_entrega }
    RobotEvent:
      type: object
      required: [delivery_id, event]
      properties:
        delivery_id: { type: integer }
        event: { type: string, enum: [LOADED, ARRIVED, UNLOCKED, FAILED] }
        reason: { type: string, nullable: true }
    Movement:
      type: object
      required: [id, type, item_id, location_id, quantity, created_at]
      properties:
        id: { type: integer }
        delivery_id: { type: integer, nullable: true }
        type: { $ref: '#/components/schemas/MovementType' }
        item_id: { type: string }
        location_id: { type: string }
        quantity: { type: integer, minimum: 1 }
        created_at: { type: string, format: date-time }
    Telemetry:
      type: object
      required: [robot_state, pose, battery, updated_at]
      properties:
        robot_state:
          type: string
          enum: [IDLE, CARREGANDO, A_CAMINHO, CHEGOU, AGUARDANDO_RETIRADA, VOLTANDO, PARADA_EMERGENCIA]
        pose:
          type: object
          required: [x, y, yaw]
          properties:
            x: { type: number }
            y: { type: number }
            yaw: { type: number, description: radianos }
        battery: { type: number, minimum: 0, maximum: 100 }
        delivery_id: { type: integer, nullable: true }
        route:
          type: array
          items:
            type: object
            properties:
              x: { type: number }
              y: { type: number }
        obstacles:
          type: array
          items:
            type: object
            properties:
              x: { type: number }
              y: { type: number }
              radius: { type: number }
        updated_at: { type: string, format: date-time }
```

- [ ] **Step 4: Escrever `docs/contracts/jwt.md`**

```markdown
# JWT

Assinado com **HS256**. O segredo vem da variável de ambiente `GERALDO_JWT_SECRET` (nunca do repositório).

| Claim | Tipo | Descrição |
|---|---|---|
| `sub` | string | id do usuário |
| `role` | string | `medico`, `enfermeiro`, `farmaceutico`, `admin` ou `robo` |
| `exp` | número | expiração (Unix); padrão de 60 minutos |
| `jti` | string | id único do token |

Regras de validação (backend):
- aceitar **somente** `HS256` (rejeitar `none` e qualquer outro algoritmo);
- exigir `exp`, `sub`, `role` e `jti`;
- token ausente, inválido ou expirado → `401`; papel sem permissão → `403`.

Cabeçalho: `Authorization: Bearer <token>`.
```

- [ ] **Step 5: Escrever `docs/contracts/ros-interfaces.md`**

```markdown
# Interfaces ROS 2 (proposta travada na semana 1)

Referencial: `map` (origem do hospital, x leste, y norte), `odom`, `base_link` (no chão, frente = +X).

## Tópicos

| Tópico | Tipo | Sentido | Semana |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Nav2 → robô | 1 |
| `/odom` | `nav_msgs/msg/Odometry` | robô → Nav2 | 1 |
| `/scan` | `sensor_msgs/msg/LaserScan` | LiDAR 2D → Nav2 | 1 |
| `/tf` | `tf2_msgs/msg/TFMessage` | robô | 1 |
| `/range/front_c` | `sensor_msgs/msg/LaserScan` | sensor a 0° | 2 |
| `/range/front_l45` | `sensor_msgs/msg/LaserScan` | sensor a +45° | 2 |
| `/range/front_r45` | `sensor_msgs/msg/LaserScan` | sensor a −45° | 2 |
| `/range/rear_l135` | `sensor_msgs/msg/LaserScan` | sensor a +135° | 2 |
| `/range/rear_r135` | `sensor_msgs/msg/LaserScan` | sensor a −135° | 2 |
| `/camera/color/image_raw` | `sensor_msgs/msg/Image` | câmera RGB-D | extra |
| `/camera/depth/image_raw` | `sensor_msgs/msg/Image` | câmera RGB-D | extra |
| `/geraldo/state` | `std_msgs/msg/String` | estado da máquina de estados | 2 |
| `/geraldo/battery` | `sensor_msgs/msg/BatteryState` | bateria | 2 |

Não há sensor a 180° (a traseira fica livre para o painel de manutenção).

## Ações e nós

- Navegação: ação `NavigateToPose` do Nav2 (`nav2_msgs/action/NavigateToPose`).
- `geraldo_dispatcher` (Samuel): chama `POST /robot/next-task`, converte `origin_waypoint` e `dest_waypoint` em poses usando `waypoints.yaml`, envia as metas ao Nav2 e reporta `POST /robot/events`.
- `waypoints.yaml`: `waypoints: { <id>: { room, x, y, yaw } }`, com `yaw` em graus.

## Estados (`/geraldo/state`)

`IDLE`, `CARREGANDO`, `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO`, `PARADA_EMERGENCIA`.
```

- [ ] **Step 6: Rodar o teste e validar o OpenAPI**

Run: `python -m pytest tools/tests/test_contracts.py -q && python -m openapi_spec_validator docs/contracts/openapi.yaml`
Expected: `7 passed` e `docs/contracts/openapi.yaml: OK`.

- [ ] **Step 7: Commit e avisar o grupo**

```bash
git add docs/contracts tools/tests/test_contracts.py
git commit -m "docs: contratos da API, JWT e interfaces ROS"
git push -u origin feat/samuel-fundacao
```

Avise o grupo: "Contratos v0 no PR de `feat/samuel-fundacao`; comentem até sábado à noite, travamos no domingo (08/11)."

---

### Task 3: Guia das IAs (AGENTS.md e prompts por papel)

> **Atualização 08/11:** esta tarefa já foi entregue. Depois dela, o grupo adotou o padrão de código da disciplina: `docs/padroes-de-projeto.md` (guia), regra 10 no `AGENTS.md`, seção de padrões nos `AGENTS.md` das pastas e `.github/pull_request_template.md`. O texto abaixo é o que foi entregue na época; vale o que está no repositório.

**Files:**
- Create: `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`
- Create: `backend/AGENTS.md`, `web/AGENTS.md`, `ros2_ws/AGENTS.md`, `security/AGENTS.md`, `unity/AGENTS.md`
- Create: `docs/prompts/00-inicio-samuel.md`, `docs/prompts/00-inicio-erik.md`, `docs/prompts/00-inicio-vieira.md`, `docs/prompts/00-inicio-pedro.md`
- Test: `tools/tests/test_agents_docs.py`

**Interfaces:**
- Consumes: estrutura de pastas (Tarefa 1) e contratos (Tarefa 2).
- Produces: o ponto de entrada das IAs de todos. Os prompts apontam para os planos `docs/superpowers/plans/2026-11-05-semana1-*.md`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_agents_docs.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AGENTS = ["AGENTS.md", "backend/AGENTS.md", "web/AGENTS.md", "ros2_ws/AGENTS.md", "security/AGENTS.md", "unity/AGENTS.md"]
PROMPTS = [f"docs/prompts/00-inicio-{n}.md" for n in ("samuel", "erik", "vieira", "pedro")]
PLAN_FOR = {
    "samuel": ["semana1-samuel-fundacao", "semana1-samuel-robo"],
    "erik": ["semana1-erik-backend"],
    "vieira": ["semana1-vieira-web"],
    "pedro": ["semana1-pedro-qualidade"],
}


def test_agents_files_exist_and_are_not_trivial():
    for rel in AGENTS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert len(text) > 300, rel


def test_root_agents_has_the_hard_rules():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for must in ("Contrato primeiro", "Movimentacao", "Nada na `main`", "segredo", "diga o plano"):
        assert must in text, must


def test_tool_pointers_reference_agents_md():
    for rel in ("CLAUDE.md", ".github/copilot-instructions.md"):
        assert "AGENTS.md" in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_prompts_reference_agents_and_their_plans():
    for person, rel in zip(("samuel", "erik", "vieira", "pedro"), PROMPTS):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "AGENTS.md" in text, rel
        for plan in PLAN_FOR[person]:
            assert plan in text, f"{rel} deveria citar {plan}"
            assert (ROOT / f"docs/superpowers/plans/2026-11-05-{plan}.md").is_file(), plan
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_agents_docs.py -q`
Expected: FAIL (arquivos não existem).

- [ ] **Step 3: Escrever `AGENTS.md` (raiz)**

````markdown
# AGENTS.md — G.E.R.A.L.D.O.

Leia este arquivo inteiro antes de qualquer tarefa. Vale para qualquer IA ou pessoa que mexa neste repositório.

## O que é

G.E.R.A.L.D.O. é um robô hospitalar autônomo, **simulado no Gazebo**, que leva medicamentos e insumos da farmácia e do banco de sangue até consultórios, enfermarias, UTI, centro cirúrgico e pronto-socorro, e atualiza o estoque do hospital conforme transporta. Demo na ExpoTech, **sábado 28/11/2026**.

Fluxo de uma entrega:

```
Pedido no sistema web → Auth JWT → Command → Fila de prioridade → Reserva de estoque
 → Despacho ao robô → Nav2 navega e desvia → Chegada → Solicitante confirma o recebimento (libera a tampa)
 → Baixa/crédito de estoque → Telemetria em todo o caminho
```

Prioridades: `critica` (sangue, drogas de emergência; exige assinatura do farmacêutico), `media` (antibióticos, fluidos), `rotina` (lençóis, inventário obsoleto; só em baixo pico).

## Documentos que mandam

1. `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` — o que e por quê.
2. `docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md` — visual.
3. `docs/contracts/` — contratos (API, ROS, JWT).
4. `docs/superpowers/plans/` — o seu plano da semana, tarefa por tarefa.

## Mapa de pastas e donos

| Pasta | Dono | Conteúdo | Guia |
|---|---|---|---|
| `modelos-3d/` | Samuel | Modelo 3D | — |
| `hospital/`, `tools/` | Samuel | `hospital.yaml` e geradores | — |
| `ros2_ws/` | Samuel | Robô, simulação, Nav2, dispatcher | `ros2_ws/AGENTS.md` |
| `backend/` | Erik | API, estoque, fila, JWT | `backend/AGENTS.md` |
| `web/` | Vieira | Sistema web responsivo | `web/AGENTS.md` |
| `design-system/` | Samuel (tokens) e Vieira (componentes) | Tokens e guia visual | — |
| `security/`, `.github/`, `tools/mock_robot.py` | Pedro | Pentest, CI, robô de mentira | `security/AGENTS.md` |
| `unity/` | Samuel (extra) | Cockpit 3D | `unity/AGENTS.md` |
| `docs/contracts/` | Samuel | Contratos | — |

## Regras duras

1. **Contrato primeiro.** Não mude um contrato sozinho. Abra um PR em `docs/contracts/` e avise o dono da frente afetada.
2. **Estoque só por `Movimentacao`.** Nunca edite saldo direto; todo efeito vira um registro imutável.
3. **Todo código novo vem com teste.** Escreva o teste, veja falhar, implemente, veja passar.
4. **Nada na `main`.** Branch `feat/<frente>-<assunto>` e Pull Request.
5. **Nenhum segredo no repositório.** Senhas, chaves e tokens vêm de variáveis de ambiente. Seeds de demonstração usam valores de teste claramente falsos.
6. **Sem hex de cor solto.** Cores só pelos tokens de `design-system/` (regras no guia).
7. **Texto de interface em português**; comandos, pastas e código em inglês. Mensagem de erro diz o que houve e o que fazer.
8. **Na dúvida, pergunte antes de inventar.** Não crie contrato, endpoint, tópico ROS ou campo novo por conta própria.
9. **Ataques de teste só contra o ambiente local** (`localhost`). Nunca contra hosts externos.

## Como rodar

| Área | Comando |
|---|---|
| Geradores e testes da raiz | `python -m pytest tools -q` |
| Backend | `cd backend && python -m pytest -q` e `uvicorn app.main:app --reload` |
| Web | `cd web && npm test -- --run` e `npm run dev` |
| Tokens do design system | `node design-system/tokens/build.mjs && (cd design-system && node --test)` |
| Simulação | `source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --symlink-install` (ver `ros2_ws/AGENTS.md`) |

## Definição de pronto (qualquer tarefa)

- Testes da área passando e nenhum teste de outra área quebrado.
- Commit pequeno, mensagem em português, no formato `tipo: o que mudou`.
- Contratos e documentação atualizados se a tarefa tocou algum deles.
- PR com descrição curta e o que foi testado.

## Como trabalhar com a IA

Antes de agir, **diga o plano**: o que vai fazer e quais arquivos vai tocar. Só depois comece. Faça uma tarefa do plano por vez e pare no commit.

## Quando travar

Falta algo de outra pessoa? Use o fixture ou a simulação indicada na própria tarefa e siga em frente; avise no grupo. Contrato errado ou ambíguo? Pare, abra PR em `docs/contracts/` e avise o Samuel.
````

- [ ] **Step 4: Escrever os ponteiros `CLAUDE.md` e `.github/copilot-instructions.md`**

`CLAUDE.md`:

```markdown
Leia o [`AGENTS.md`](AGENTS.md) na raiz antes de qualquer tarefa; ele vale para esta ferramenta também. Depois leia o `AGENTS.md` da pasta onde você vai trabalhar.
```

`.github/copilot-instructions.md`: (mesmo texto, com o link `../AGENTS.md`):

```markdown
Leia o [`AGENTS.md`](../AGENTS.md) na raiz antes de qualquer tarefa; ele vale para esta ferramenta também. Depois leia o `AGENTS.md` da pasta onde você vai trabalhar.
```

- [ ] **Step 5: Escrever os guias das pastas**

`backend/AGENTS.md`:

````markdown
# backend/AGENTS.md — API e gestão hospitalar (dono: Erik)

Stack: Python 3.11+, FastAPI, SQLModel (SQLite no começo), PyJWT, pytest, httpx.

## Comandos

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

## Padrões

- **Command:** cada ação do domínio (criar, cancelar, aprovar entrega) é uma classe em `app/commands/` com método `execute()`. Os routers só validam a entrada, chamam o comando e traduzem exceções do domínio em HTTP.
- **Estoque só por `Movimentacao`** (`RESERVA`, `BAIXA`, `CREDITO`, `ESTORNO`). `quantity` do movimento é sempre positiva; o tipo diz a direção.
- **Prioridade:** `critica` < `media` < `rotina`; dentro da mesma prioridade, FIFO por `id`.
- **JWT:** somente HS256; exigir `exp`, `sub`, `role`, `jti`. Segredo em `GERALDO_JWT_SECRET`.
- Mensagens de erro em português, no formato "o que houve + o que fazer".

## O que não tocar

`docs/contracts/` (mudança só por PR com aviso ao Samuel). Respostas da API devem bater com `docs/contracts/openapi.yaml`; o teste de contrato do Pedro (`backend/tests/test_contract.py`) falha se não baterem.

## Variáveis de ambiente

`GERALDO_DATABASE_URL`, `GERALDO_JWT_SECRET`, `GERALDO_JWT_MINUTES`, `GERALDO_DEMO_PASSWORD` (senha dos usuários de demonstração), `GERALDO_AUTO_SEED`.
````

`web/AGENTS.md`:

````markdown
# web/AGENTS.md — sistema web responsivo (dono: Vieira)

Stack: React + Vite + TypeScript + Tailwind v3, Vitest + Testing Library, MSW para simular a API. Os padrões de projeto da disciplina ficam em `src/domain/` e `src/apresentacao/`; siga o padrão que já existe lá.

## Comandos

```bash
cd web
npm install
npm test -- --run
npm run dev
npm run build
```

## Regras (do design system)

- **Sem hex solto:** só classes do preset (`bg-azul-500`, `text-vermelho-600`, `rounded-card`...) ou `var(--azul-500)`.
- **Vermelho só para:** prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro.
- **Um botão primário por tela.** Status nunca só por cor: sempre cor + ícone ou texto.
- **Mobile-first;** alvo de toque mínimo de 44 px (`min-h-controle`).
- Números com `tabular-nums`. Texto em português, *sentence case*, botão com verbo curto ("Solicitar medicamento"), sem "por favor".
- Ícones: `lucide-react`.

## Dados

Consuma só a API do contrato (`docs/contracts/openapi.yaml`). Enquanto o backend não estiver pronto, use os handlers MSW em `src/api/mocks/`.
````

`ros2_ws/AGENTS.md`:

````markdown
# ros2_ws/AGENTS.md — robô e simulação (dono: Samuel)

Stack: ROS 2 Jazzy + Gazebo Harmonic 8 + Nav2, **nativos** na máquina do Samuel (Pop!_OS 24.04), que também é a máquina da demo. A versão final é confirmada com a disciplina. Docker é opcional (semana 2).

## Comandos

```bash
bash tools/check_ros_env.sh                      # confere o ambiente (deve imprimir AMBIENTE OK)
source /opt/ros/jazzy/setup.bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch geraldo_description sim.launch.py headless:=true
```

## Convenções

- Referencial: `map` → `odom` → `base_link` (no chão; frente = +X). Unidades em metros e radianos.
- Rodas: `wheel_left_joint` e `wheel_right_joint` (eixo Y), separação de 0,45 m, raio de 0,10 m.
- Footprint do Nav2: retângulo 0,70 × 0,50 m (+10 cm de inflação).
- Tópicos e estados: `docs/contracts/ros-interfaces.md`. Não crie tópico novo sem PR no contrato.
- O mundo, o mapa e os waypoints são **gerados** por `tools/gen_hospital.py`; não edite os arquivos gerados à mão.
````

`security/AGENTS.md`:

````markdown
# security/AGENTS.md — pentest e qualidade (dono: Pedro)

Escopo: atacar **somente o ambiente local** (`http://localhost:8000`). Nunca contra hosts externos.

## Ataques demonstráveis (cinco)

1. Requisição falsificada (sem `Authorization`, ou com papel forjado).
2. JWT adulterado, expirado ou com `alg: none`.
3. Escalada de papel (enfermaria pedindo prioridade crítica; outro usuário confirmando o recebimento de uma entrega alheia).
4. Injeção nos campos (SQL, texto malicioso em `item_id`, `dest_id`).
5. Injeção de obstáculo falso na telemetria.

Cada ataque tem: script em `security/attacks/`, teste automatizado que falha antes da mitigação e passa depois, e uma seção no relatório `security/RELATORIO.md` (antes/depois).

## Também é seu

CI em `.github/workflows/`, teste de contrato em `backend/tests/test_contract.py`, robô de mentira em `tools/mock_robot.py` e a coleção de requests em `security/requests/`.
````

`unity/AGENTS.md`:

````markdown
# unity/AGENTS.md — cockpit 3D (extra; dono: Samuel)

É o **primeiro corte** se o prazo apertar; só começa depois do M2 (18/11).

- Modelo do robô: `modelos-3d/geraldoV1.glb`.
- Cores: `design-system/dist/GeraldoTokens.cs` (não edite à mão).
- Dados: `GET /telemetry` e `WS /ws/telemetry` (contrato em `docs/contracts/openapi.yaml`).
- Alvo: desktop e celular.
````

- [ ] **Step 6: Escrever os prompts de partida**

`docs/prompts/00-inicio-samuel.md`:

````markdown
# Prompt de partida — Samuel (robô, simulação, hospital, contratos)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, ros2_ws/AGENTS.md, a spec em
docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md e os planos
docs/superpowers/plans/2026-11-05-semana1-samuel-fundacao.md e
docs/superpowers/plans/2026-11-05-semana1-samuel-robo.md.

Minha frente: robô e simulação (URDF, Gazebo, Nav2), hospital (hospital.yaml e geradores),
contratos e tokens do design system.

Tarefa: execute os planos tarefa por tarefa, na ordem do docs/superpowers/plans/README.md.
Não mude contratos já travados sem me avisar. Não toque em backend/, web/ nem security/.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
````

`docs/prompts/00-inicio-erik.md`:

````markdown
# Prompt de partida — Erik (backend)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, backend/AGENTS.md, docs/contracts/openapi.yaml,
docs/contracts/jwt.md e o plano docs/superpowers/plans/2026-11-05-semana1-erik-backend.md.

Minha frente: backend e gestão hospitalar (FastAPI, estoque, fila, JWT).

Tarefa: execute o plano tarefa por tarefa, começando pela Tarefa 1. Cada tarefa é TDD:
teste que falha, implementação mínima, teste que passa, commit.
Não mude docs/contracts/ sem PR e aviso ao Samuel. Não toque em web/, ros2_ws/ nem security/.
Estoque só muda por Movimentacao.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
````

`docs/prompts/00-inicio-vieira.md`:

````markdown
# Prompt de partida — Vieira (sistema web)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, web/AGENTS.md, a spec do design system
docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md, docs/contracts/openapi.yaml
e o plano docs/superpowers/plans/2026-11-05-semana1-vieira-web.md.

Minha frente: sistema web responsivo (solicitar medicamento, acompanhar entregas, painel).

Tarefa: execute o plano tarefa por tarefa, começando pela Tarefa 1. Cada tarefa é TDD.
Use só cores e medidas dos tokens do design system (nada de hex solto). Mobile-first.
Enquanto o backend não estiver pronto, use os handlers MSW. Não mude docs/contracts/ sem PR
e aviso ao Samuel. Não toque em backend/, ros2_ws/ nem security/.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
````

`docs/prompts/00-inicio-pedro.md`:

````markdown
# Prompt de partida — Pedro (qualidade e segurança)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, security/AGENTS.md, docs/contracts/openapi.yaml
e o plano docs/superpowers/plans/2026-11-05-semana1-pedro-qualidade.md.

Minha frente: qualidade e segurança (CI, teste de contrato, robô de mentira e, na semana 3, pentest).

Tarefa: execute o plano tarefa por tarefa, começando pela Tarefa 1. Cada tarefa é TDD quando há código.
Ataques de teste só contra localhost. Não mude docs/contracts/ sem PR e aviso ao Samuel.
Não implemente funcionalidades do backend, da web nem do robô: a sua frente é testá-las.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
````

- [ ] **Step 7: Rodar o teste**

Run: `python -m pytest tools/tests/test_agents_docs.py -q`
Expected: os testes de existência e de conteúdo passam. O teste `test_prompts_reference_agents_and_their_plans` só passa quando os cinco planos existirem em `docs/superpowers/plans/` (eles vêm no mesmo PR de documentação); se rodar antes disso, o único erro esperado é "plano não encontrado".

- [ ] **Step 8: Commit**

```bash
git add AGENTS.md CLAUDE.md .github docs/prompts backend/AGENTS.md web/AGENTS.md ros2_ws/AGENTS.md security/AGENTS.md unity/AGENTS.md tools/tests/test_agents_docs.py
git commit -m "docs: guia das IAs (AGENTS.md) e prompts por papel"
```

---

### Task 4: Hospital gerado de `hospital.yaml`

**Files:**
- Create: `hospital/hospital.yaml`, `tools/gen_hospital.py`
- Test: `tools/tests/test_gen_hospital.py`
- Create (gerados): `ros2_ws/src/geraldo_description/worlds/hospital.sdf`, `ros2_ws/src/geraldo_nav/maps/hospital.pgm`, `ros2_ws/src/geraldo_nav/maps/hospital.yaml`, `ros2_ws/src/geraldo_nav/config/waypoints.yaml`, `backend/seeds/locais.json`

**Interfaces:**
- Consumes: spec §3 (salas, portas, waypoints).
- Produces (usados por outros planos):
  - `tools.gen_hospital.load_spec(path) -> dict`
  - `tools.gen_hospital.rasterize(spec, extra_obstacles=()) -> np.ndarray[bool]` (True = ocupado; linha 0 = y máximo)
  - `tools.gen_hospital.inflate(occ, radius_cells) -> np.ndarray[bool]`
  - `tools.gen_hospital.cell_of(x, y, spec) -> tuple[int, int]` (linha, coluna)
  - `tools.gen_hospital.distances(blocked, start) -> np.ndarray[int32]` (−1 = inalcançável)
  - `locais.json`: lista de `{id, name, kind, has_stock, waypoint}`; `waypoints.yaml`: `waypoints: {id: {room, x, y, yaw}}` com `yaw` em graus.

- [ ] **Step 1: Escrever `hospital/hospital.yaml`**

```yaml
version: 1
size: [46, 30]            # largura (x) e altura (y), em metros
resolution: 0.05          # metros por célula do mapa
wall_thickness: 0.15
wall_height: 2.5
door_width: 1.0
corridor_width: 2.0
robot_inscribed_radius: 0.25   # meia largura do robô
robot_margin: 0.10             # folga de inflação
entrances:                # portas na parede externa
  - { id: principal, wall: S, at: 7 }
  - { id: ambulancia, wall: W, at: 11 }
rooms:
  - id: farmacia
    name: Farmácia central
    kind: pharmacy
    rect: [2, 16, 12, 28]
    stock: true
    doors: [{ wall: N, at: 7 }, { wall: S, at: 7 }]
    stop: farmacia_balcao
    waypoints:
      - { id: base_robo, xy: [6.5, 26.5], yaw: 270 }
      - { id: farmacia_balcao, xy: [7, 24], yaw: 270 }
  - id: banco_sangue
    name: Banco de sangue
    kind: blood_bank
    rect: [12, 22, 22, 28]
    stock: true
    doors: [{ wall: N, at: 17 }]
    stop: banco_sangue_retirada
    waypoints:
      - { id: banco_sangue_retirada, xy: [17, 25], yaw: 90 }
  - id: apoio
    name: Apoio (rouparia)
    kind: support
    rect: [12, 16, 22, 22]
    stock: false
    doors: [{ wall: S, at: 17 }]
    stop: rouparia_coleta
    waypoints:
      - { id: rouparia_coleta, xy: [17, 18.5], yaw: 270 }
  - id: centro_cirurgico
    name: Centro cirúrgico
    kind: surgery
    rect: [24, 16, 34, 28]
    stock: true
    doors: [{ wall: N, at: 29 }, { wall: S, at: 29 }]
    stop: cc_entrega
    waypoints:
      - { id: cc_entrega, xy: [29, 25], yaw: 90 }
  - id: uti
    name: UTI
    kind: icu
    rect: [34, 16, 44, 28]
    stock: true
    doors: [{ wall: N, at: 39 }, { wall: S, at: 39 }]
    stop: uti_entrega
    waypoints:
      - { id: uti_entrega, xy: [39, 25], yaw: 90 }
  - id: pronto_socorro
    name: Pronto-socorro
    kind: emergency
    rect: [2, 8, 22, 14]
    stock: true
    doors: [{ wall: N, at: 12 }, { wall: W, at: 11 }]
    stop: ps_entrega
    waypoints:
      - { id: ps_entrega, xy: [12, 11], yaw: 90 }
  - id: recepcao
    name: Recepção
    kind: reception
    rect: [2, 2, 12, 8]
    stock: false
    doors: [{ wall: S, at: 7 }]
    waypoints: []
  - id: consultorio1
    name: Consultório 1
    kind: office
    rect: [12, 2, 17, 8]
    stock: true
    doors: [{ wall: S, at: 14.5 }]
    stop: cons1_entrega
    waypoints:
      - { id: cons1_entrega, xy: [14.5, 4], yaw: 270 }
  - id: consultorio2
    name: Consultório 2
    kind: office
    rect: [17, 2, 22, 8]
    stock: true
    doors: [{ wall: S, at: 19.5 }]
    stop: cons2_entrega
    waypoints:
      - { id: cons2_entrega, xy: [19.5, 4], yaw: 270 }
  - id: enfermaria214
    name: Enfermaria 214
    kind: ward
    rect: [24, 2, 34, 14]
    stock: true
    doors: [{ wall: N, at: 29 }, { wall: S, at: 29 }]
    stop: enf214_entrega
    waypoints:
      - { id: enf214_entrega, xy: [29, 12], yaw: 270 }
  - id: enfermaria215
    name: Enfermaria 215
    kind: ward
    rect: [34, 2, 44, 14]
    stock: true
    doors: [{ wall: N, at: 39 }, { wall: S, at: 39 }]
    stop: enf215_entrega
    waypoints:
      - { id: enf215_entrega, xy: [39, 12], yaw: 270 }
```

- [ ] **Step 2: Escrever os testes (falham primeiro)**

Create `tools/tests/test_gen_hospital.py`:

```python
from pathlib import Path

import numpy as np
import pytest

from tools import gen_hospital as g

ROOT = Path(__file__).resolve().parents[2]
SPEC = g.load_spec(ROOT / "hospital" / "hospital.yaml")
INFLATE_CELLS = round((SPEC["robot_inscribed_radius"] + SPEC["robot_margin"]) / SPEC["resolution"])
NORTH_CORRIDOR_BLOCK = (22.0, 28.0, 24.0, 30.0)  # maca no cruzamento do corredor norte


def all_waypoints():
    out = {}
    for room in SPEC["rooms"]:
        for wp in room["waypoints"]:
            out[wp["id"]] = (room, wp)
    return out


@pytest.fixture(scope="module")
def grid():
    return g.rasterize(SPEC)


@pytest.fixture(scope="module")
def inflated(grid):
    return g.inflate(grid, INFLATE_CELLS)


def test_room_ids_match_the_contract():
    assert {r["id"] for r in SPEC["rooms"]} == {
        "farmacia", "banco_sangue", "apoio", "centro_cirurgico", "uti", "pronto_socorro",
        "recepcao", "consultorio1", "consultorio2", "enfermaria214", "enfermaria215",
    }


def test_every_waypoint_is_inside_its_room_with_margin():
    for wid, (room, wp) in all_waypoints().items():
        x0, y0, x1, y1 = room["rect"]
        x, y = wp["xy"]
        assert x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5, wid


def test_every_stop_points_to_a_real_waypoint():
    wps = all_waypoints()
    for room in SPEC["rooms"]:
        if room.get("stop"):
            assert room["stop"] in wps, room["id"]


def test_waypoints_are_free_after_inflation(inflated):
    for wid, (_, wp) in all_waypoints().items():
        r, c = g.cell_of(*wp["xy"], SPEC)
        assert not inflated[r, c], wid


def test_all_waypoints_reachable_from_base(inflated):
    r, c = g.cell_of(*all_waypoints()["base_robo"][1]["xy"], SPEC)
    dist = g.distances(inflated, (r, c))
    unreachable = [w for w, (_, wp) in all_waypoints().items() if dist[g.cell_of(*wp["xy"], SPEC)] < 0]
    assert not unreachable, unreachable


def test_alternative_route_exists_when_north_corridor_is_blocked(grid):
    blocked = g.inflate(g.rasterize(SPEC, extra_obstacles=[NORTH_CORRIDOR_BLOCK]), INFLATE_CELLS)
    free = g.inflate(grid, INFLATE_CELLS)
    wps = all_waypoints()
    src = g.cell_of(*wps["banco_sangue_retirada"][1]["xy"], SPEC)
    dst = g.cell_of(*wps["cc_entrega"][1]["xy"], SPEC)
    normal = g.distances(free, src)[dst]
    detour = g.distances(blocked, src)[dst]
    assert normal > 0, "sem rota normal"
    assert detour > 0, "sem rota alternativa com a maca"
    assert detour > 2 * normal, f"a rota alternativa deveria ser bem mais longa ({detour} vs {normal})"


def test_doors_are_open_at_their_center(grid):
    for room in SPEC["rooms"]:
        x0, y0, x1, y1 = room["rect"]
        for d in room["doors"]:
            at = d["at"]
            probe = {"N": (at, y1), "S": (at, y0), "W": (x0, at), "E": (x1, at)}[d["wall"]]
            r, c = g.cell_of(*probe, SPEC)
            assert not grid[r, c], f"{room['id']} porta {d}"


def test_outputs_are_written(tmp_path):
    out = {
        "world": tmp_path / "hospital.sdf",
        "map_dir": tmp_path / "maps",
        "locais": tmp_path / "locais.json",
        "waypoints": tmp_path / "waypoints.yaml",
    }
    g.generate(ROOT / "hospital" / "hospital.yaml", **out)
    assert out["world"].read_text().startswith("<?xml")
    pgm = (out["map_dir"] / "hospital.pgm").read_bytes()
    assert pgm.startswith(b"P5\n920 600\n255\n")
    assert len(pgm) == len(b"P5\n920 600\n255\n") + 920 * 600
    assert "resolution: 0.05" in (out["map_dir"] / "hospital.yaml").read_text()
    import json
    locais = json.loads(out["locais"].read_text(encoding="utf-8"))
    assert {l["id"] for l in locais} == {r["id"] for r in SPEC["rooms"]}
    assert next(l for l in locais if l["id"] == "farmacia")["waypoint"] == "farmacia_balcao"
    assert next(l for l in locais if l["id"] == "recepcao")["waypoint"] is None
    import yaml
    wps = yaml.safe_load(out["waypoints"].read_text(encoding="utf-8"))["waypoints"]
    assert wps["cc_entrega"] == {"room": "centro_cirurgico", "x": 29, "y": 25, "yaw": 90}
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pip install numpy pyyaml pytest && python -m pytest tools/tests/test_gen_hospital.py -q`
Expected: FAIL (`tools.gen_hospital` não existe).

- [ ] **Step 4: Implementar `tools/gen_hospital.py`**

```python
#!/usr/bin/env python3
"""Gera mundo (SDF), mapa de ocupação, locais.json e waypoints.yaml a partir de hospital/hospital.yaml.

Referencial: origem no canto sudoeste; x para leste, y para norte (metros).
"""
from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
Segment = tuple[float, float, float, float]  # x0, y0, x1, y1 (eixo alinhado)


def load_spec(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


# ---------- geometria das paredes ----------
def _with_gaps(p0: float, p1: float, gaps: list[float], door_w: float) -> list[tuple[float, float]]:
    """Divide o intervalo [p0, p1] deixando vãos de largura door_w centrados em `gaps`."""
    cuts = sorted((a - door_w / 2, a + door_w / 2) for a in gaps)
    out, cur = [], p0
    for lo, hi in cuts:
        if lo > cur:
            out.append((cur, lo))
        cur = max(cur, hi)
    if cur < p1:
        out.append((cur, p1))
    return out


def _wall(wall: str, rect: tuple[float, float, float, float], gaps: list[float], door_w: float) -> list[Segment]:
    x0, y0, x1, y1 = rect
    if wall in ("N", "S"):
        y = y1 if wall == "N" else y0
        return [(a, y, b, y) for a, b in _with_gaps(x0, x1, gaps, door_w)]
    x = x1 if wall == "E" else x0
    return [(x, a, x, b) for a, b in _with_gaps(y0, y1, gaps, door_w)]


def wall_segments(spec: dict) -> list[Segment]:
    # cada ponta de parede é engrossada em meia espessura; alargamos o vão para a abertura livre ficar com door_width
    door_w = spec["door_width"] + spec["wall_thickness"]
    segs: list[Segment] = []
    for room in spec["rooms"]:
        rect = tuple(room["rect"])
        for wall in "NSWE":
            gaps = [d["at"] for d in room["doors"] if d["wall"] == wall]
            segs += _wall(wall, rect, gaps, door_w)
    w, h = spec["size"]
    outer = (0.0, 0.0, float(w), float(h))
    for wall in "NSWE":
        gaps = [e["at"] for e in spec["entrances"] if e["wall"] == wall]
        segs += _wall(wall, outer, gaps, door_w)
    return segs


# ---------- mapa de ocupação ----------
def grid_shape(spec: dict) -> tuple[int, int]:
    res = spec["resolution"]
    w, h = spec["size"]
    return round(h / res), round(w / res)  # linhas, colunas


def cell_of(x: float, y: float, spec: dict) -> tuple[int, int]:
    rows, cols = grid_shape(spec)
    res = spec["resolution"]
    return min(rows - 1, max(0, rows - 1 - int(y / res))), min(cols - 1, max(0, int(x / res)))


def _fill(occ: np.ndarray, rect: tuple[float, float, float, float], spec: dict) -> None:
    rows, cols = occ.shape
    res = spec["resolution"]
    x0, y0, x1, y1 = rect
    c0, c1 = max(0, int(np.floor(x0 / res))), min(cols, int(np.ceil(x1 / res)))
    r0, r1 = max(0, rows - int(np.ceil(y1 / res))), min(rows, rows - int(np.floor(y0 / res)))
    occ[r0:r1, c0:c1] = True


def rasterize(spec: dict, extra_obstacles=()) -> np.ndarray:
    occ = np.zeros(grid_shape(spec), dtype=bool)
    half = spec["wall_thickness"] / 2
    for x0, y0, x1, y1 in wall_segments(spec):
        _fill(occ, (min(x0, x1) - half, min(y0, y1) - half, max(x0, x1) + half, max(y0, y1) + half), spec)
    for rect in extra_obstacles:
        _fill(occ, rect, spec)
    return occ


def _shift_or(dst: np.ndarray, src: np.ndarray, dr: int, dc: int) -> None:
    rows, cols = src.shape
    r0, r1 = max(0, dr), min(rows, rows + dr)
    c0, c1 = max(0, dc), min(cols, cols + dc)
    dst[r0:r1, c0:c1] |= src[r0 - dr : r1 - dr, c0 - dc : c1 - dc]


def inflate(occ: np.ndarray, radius_cells: int) -> np.ndarray:
    out = occ.copy()
    for dr in range(-radius_cells, radius_cells + 1):
        for dc in range(-radius_cells, radius_cells + 1):
            if dr * dr + dc * dc <= radius_cells * radius_cells and (dr or dc):
                _shift_or(out, occ, dr, dc)
    return out


def distances(blocked: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Distância em células (vizinhança de 4) a partir de `start`; -1 se inalcançável."""
    rows, cols = blocked.shape
    dist = np.full(blocked.shape, -1, dtype=np.int32)
    if blocked[start]:
        return dist
    dist[start] = 0
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        d = dist[r, c] + 1
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and not blocked[nr, nc] and dist[nr, nc] < 0:
                dist[nr, nc] = d
                queue.append((nr, nc))
    return dist


# ---------- escritores ----------
def write_pgm(occ: np.ndarray, path: Path) -> None:
    rows, cols = occ.shape
    pixels = np.where(occ, 0, 254).astype(np.uint8)  # 0 = ocupado (preto), 254 = livre
    path.write_bytes(f"P5\n{cols} {rows}\n255\n".encode("ascii") + pixels.tobytes())


def write_map_yaml(spec: dict, path: Path) -> None:
    path.write_text(
        "image: hospital.pgm\n"
        "mode: trinary\n"
        f"resolution: {spec['resolution']}\n"
        "origin: [0.0, 0.0, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.25\n",
        encoding="utf-8",
    )


def write_sdf(spec: dict, path: Path) -> None:
    t, h = spec["wall_thickness"], spec["wall_height"]
    models = []
    for i, (x0, y0, x1, y1) in enumerate(wall_segments(spec)):
        horizontal = abs(y1 - y0) < 1e-9
        length = abs(x1 - x0) if horizontal else abs(y1 - y0)
        if length < 1e-6:
            continue
        sx, sy = (length + t, t) if horizontal else (t, length + t)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        models.append(
            f'    <model name="wall_{i}"><static>true</static><pose>{cx:.3f} {cy:.3f} {h / 2:.3f} 0 0 0</pose>'
            f'<link name="link"><collision name="c"><geometry><box><size>{sx:.3f} {sy:.3f} {h}</size></box></geometry></collision>'
            f'<visual name="v"><geometry><box><size>{sx:.3f} {sy:.3f} {h}</size></box></geometry>'
            f'<material><ambient>0.85 0.87 0.9 1</ambient><diffuse>0.85 0.87 0.9 1</diffuse></material></visual></link></model>'
        )
    w, d = spec["size"]
    xml = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="hospital">
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>{w / 2} {d / 2} 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse><specular>0.2 0.2 0.2 1</specular><direction>-0.3 0.2 -1</direction></light>
    <model name="ground"><static>true</static><pose>{w / 2} {d / 2} 0 0 0 0</pose>
      <link name="link"><collision name="c"><geometry><plane><normal>0 0 1</normal><size>{w + 4} {d + 4}</size></plane></geometry></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal><size>{w + 4} {d + 4}</size></plane></geometry>
      <material><ambient>0.7 0.72 0.76 1</ambient><diffuse>0.7 0.72 0.76 1</diffuse></material></visual></link></model>
{chr(10).join(models)}
  </world>
</sdf>
"""
    path.write_text(xml, encoding="utf-8")


def write_locais(spec: dict, path: Path) -> None:
    locais = [
        {
            "id": r["id"],
            "name": r["name"],
            "kind": r["kind"],
            "has_stock": bool(r["stock"]),
            "waypoint": r.get("stop"),
        }
        for r in spec["rooms"]
    ]
    path.write_text(json.dumps(locais, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_waypoints(spec: dict, path: Path) -> None:
    wps = {}
    for r in spec["rooms"]:
        for wp in r["waypoints"]:
            x, y = wp["xy"]
            wps[wp["id"]] = {"room": r["id"], "x": x, "y": y, "yaw": wp["yaw"]}
    path.write_text(yaml.safe_dump({"waypoints": wps}, sort_keys=False, allow_unicode=True), encoding="utf-8")


def generate(spec_path, world, map_dir, locais, waypoints) -> None:
    spec = load_spec(spec_path)
    for p in (Path(world), Path(map_dir) / "x", Path(locais), Path(waypoints)):
        p.parent.mkdir(parents=True, exist_ok=True)
    write_sdf(spec, Path(world))
    occ = rasterize(spec)
    write_pgm(occ, Path(map_dir) / "hospital.pgm")
    write_map_yaml(spec, Path(map_dir) / "hospital.yaml")
    write_locais(spec, Path(locais))
    write_waypoints(spec, Path(waypoints))


def main() -> None:
    desc = ROOT / "ros2_ws/src/geraldo_description"
    nav = ROOT / "ros2_ws/src/geraldo_nav"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", default=str(ROOT / "hospital/hospital.yaml"))
    ap.add_argument("--world", default=str(desc / "worlds/hospital.sdf"))
    ap.add_argument("--map-dir", default=str(nav / "maps"))
    ap.add_argument("--locais", default=str(ROOT / "backend/seeds/locais.json"))
    ap.add_argument("--waypoints", default=str(nav / "config/waypoints.yaml"))
    a = ap.parse_args()
    generate(a.spec, a.world, a.map_dir, a.locais, a.waypoints)
    print("hospital gerado")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Rodar os testes e ver passar**

Run: `python -m pytest tools/tests/test_gen_hospital.py -q`
Expected: `9 passed`. O teste `test_alternative_route_exists_when_north_corridor_is_blocked` roda 2 buscas em largura (≈ 2–4 s cada). Se alguma porta não abrir passagem, o teste `test_doors_open_a_passage_wider_than_the_robot` ou o de alcance mostra qual sala; ajuste o `at` no YAML e rode de novo.

- [ ] **Step 6: Gerar os arquivos do hospital e conferir**

```bash
python tools/gen_hospital.py
ls -la ros2_ws/src/geraldo_description/worlds/hospital.sdf ros2_ws/src/geraldo_nav/maps/ ros2_ws/src/geraldo_nav/config/waypoints.yaml backend/seeds/locais.json
head -c 15 ros2_ws/src/geraldo_nav/maps/hospital.pgm | head -2
```

Expected: os 5 arquivos existem; o PGM começa com `P5` e `920 600`.

- [ ] **Step 7: Commit**

```bash
git add hospital tools ros2_ws backend/seeds
git commit -m "feat: hospital gerado de hospital.yaml (mundo, mapa, locais e waypoints)"
```

Avise o Erik: `backend/seeds/locais.json` está pronto (ids dos locais e waypoints).

---

### Task 5: Tokens do design system

> **Já feito em 08/11/2026 (direto na `main`):** `design-system/tokens/` (tokens, gerador e contraste), `design-system/tests/` e `design-system/dist/` estão no repositório, com os testes passando. Depois, o `branco` passou de branco puro para `#FAFBFD` e entrou `design-system/tests/palette.test.mjs` (nenhuma cor pode ser branco ou preto puro). Use este bloco só como referência do que foi feito.

**Files:**
- Create: `design-system/tokens/tokens.json`, `design-system/tokens/build.mjs`, `design-system/tokens/contrast.mjs`
- Create (gerados): `design-system/dist/tokens.css`, `design-system/dist/tailwind.preset.cjs`, `design-system/dist/GeraldoTokens.cs`
- Test: `design-system/tests/build.test.mjs`, `design-system/tests/contrast.test.mjs`

**Interfaces:**
- Consumes: DS spec §3 a §7 (valores exatos).
- Produces:
  - `build(tokens, outDir)` em `build.mjs` (grava os 3 arquivos); CLI: `node design-system/tokens/build.mjs`.
  - `contrastRatio(hexA, hexB) -> number` e `PAIRS` em `contrast.mjs`.
  - Preset do Tailwind: cores `azul-*`, `vermelho-*`, `neutro-*`, `sucesso-*`, `aviso-*`, `fundo`, `branco`, `tinta`; `fontFamily.display` e `fontFamily.sans`; `borderRadius` `card`, `controle`, `pequeno`; `boxShadow` `card`, `popover`, `dialog`; `minHeight.controle` e `minWidth.controle` (44 px); `screens`.
  - Variáveis CSS: `--azul-500`, `--vermelho-500`, `--neutro-100`, `--fundo`, `--branco`, `--tinta`, `--font-display`, `--font-body`, `--radius-card`, `--shadow-card`...
  - C#: `Geraldo.GeraldoTokens.Azul500` etc. (`Color32`).

- [ ] **Step 1: Escrever `design-system/tokens/tokens.json`**

```json
{
  "color": {
    "azul": { "50": "#EEF3FF", "100": "#DCE6FF", "200": "#B9CCFF", "300": "#8FAEFF", "400": "#5C86F5", "500": "#3A66E8", "600": "#2B52C9", "700": "#223F9C", "800": "#1A3074", "900": "#12214F" },
    "vermelho": { "50": "#FEF1F1", "100": "#FDDCDC", "200": "#F9B4B8", "300": "#F38A91", "400": "#EB5963", "500": "#D92D3A", "600": "#B91C2B", "700": "#8C1522", "800": "#650F18", "900": "#42090F" },
    "neutro": { "50": "#EEF1F7", "100": "#E5E9F2", "200": "#D3D9E6", "300": "#B6BED0", "400": "#8F98AD", "500": "#636B7E", "600": "#4A5266", "700": "#323A4D", "800": "#1B2233", "900": "#0F1422" },
    "sucesso": { "50": "#E8F6EE", "500": "#1F9D61", "700": "#146B41" },
    "aviso": { "50": "#FEF5E3", "500": "#E39A1B", "700": "#8A5A07" },
    "fundo": "#F4F6FB",
    "branco": "#FAFBFD",
    "tinta": "#1B2233"
  },
  "font": {
    "display": ["Plus Jakarta Sans", "system-ui", "sans-serif"],
    "body": ["Inter", "system-ui", "sans-serif"]
  },
  "radius": { "card": "16px", "controle": "12px", "pequeno": "8px", "pilula": "9999px" },
  "shadow": {
    "card": "0 1px 2px rgba(18,33,79,.04), 0 4px 16px rgba(18,33,79,.06)",
    "popover": "0 8px 24px rgba(18,33,79,.12)",
    "dialog": "0 16px 40px rgba(18,33,79,.18)"
  },
  "screens": { "sm": "640px", "md": "768px", "lg": "1024px", "xl": "1280px" },
  "size": { "altura-controle": "44px", "largura-sidebar": "72px", "largura-max": "1280px" }
}
```

- [ ] **Step 2: Escrever os testes (falham primeiro)**

Create `design-system/tests/contrast.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { contrastRatio, PAIRS, hexOf } from "../tokens/contrast.mjs";

const tokens = JSON.parse(readFileSync(new URL("../tokens/tokens.json", import.meta.url)));

test("contrastRatio: preto sobre branco é 21", () => {
  assert.equal(Math.round(contrastRatio("#000000", "#FFFFFF")), 21);
});

test("contrastRatio é simétrico", () => {
  assert.equal(contrastRatio("#3A66E8", "#FFFFFF"), contrastRatio("#FFFFFF", "#3A66E8"));
});

for (const [fg, bg, min] of PAIRS) {
  test(`contraste ${fg} sobre ${bg} >= ${min}`, () => {
    const ratio = contrastRatio(hexOf(tokens, fg), hexOf(tokens, bg));
    assert.ok(ratio >= min, `${fg} sobre ${bg} = ${ratio.toFixed(2)} (mínimo ${min})`);
  });
}
```

Create `design-system/tests/build.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { build } from "../tokens/build.mjs";

const tokens = JSON.parse(readFileSync(new URL("../tokens/tokens.json", import.meta.url)));
const out = mkdtempSync(join(tmpdir(), "gd-"));
build(tokens, out);
const css = readFileSync(join(out, "tokens.css"), "utf8");
const preset = readFileSync(join(out, "tailwind.preset.cjs"), "utf8");
const cs = readFileSync(join(out, "GeraldoTokens.cs"), "utf8");

test("tokens.css tem variáveis de cor, fonte, raio e sombra", () => {
  assert.match(css, /--azul-500: #3A66E8;/);
  assert.match(css, /--vermelho-500: #D92D3A;/);
  assert.match(css, /--fundo: #F4F6FB;/);
  assert.match(css, /--font-display: 'Plus Jakarta Sans', system-ui, sans-serif;/);
  assert.match(css, /--radius-card: 16px;/);
  assert.match(css, /--shadow-card: 0 1px 2px/);
});

test("preset do Tailwind carrega e expõe as chaves esperadas", async () => {
  const mod = await import(pathToFileURL(join(out, "tailwind.preset.cjs")).href);
  const theme = (mod.default ?? mod).theme.extend;
  assert.equal(theme.colors.azul[500], "#3A66E8");
  assert.equal(theme.colors.fundo, "#F4F6FB");
  assert.equal(theme.borderRadius.card, "16px");
  assert.equal(theme.minHeight.controle, "44px");
  assert.equal(theme.minWidth.controle, "44px");
  assert.deepEqual(theme.fontFamily.display, ["Plus Jakarta Sans", "system-ui", "sans-serif"]);
  assert.equal(theme.screens.md, "768px");
  assert.ok(preset.includes("module.exports"));
});

test("GeraldoTokens.cs tem Color32 para cada cor", () => {
  assert.match(cs, /public static readonly Color32 Azul500 = new Color32\(0x3A, 0x66, 0xE8, 0xFF\);/);
  assert.match(cs, /public static readonly Color32 Fundo = new Color32\(0xF4, 0xF6, 0xFB, 0xFF\);/);
  assert.match(cs, /namespace Geraldo/);
});
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `(cd design-system && node --test)`
Expected: FAIL (módulos `build.mjs` e `contrast.mjs` não existem).

- [ ] **Step 4: Implementar `design-system/tokens/contrast.mjs`**

```js
// Contraste WCAG entre pares de tokens usados nos componentes (DS §3.6).
export function hexOf(tokens, name) {
  const [group, step] = name.split("-");
  const c = tokens.color;
  return step === undefined ? c[group] : c[group][step];
}

function channel(v) {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function luminance(hex) {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}

export function contrastRatio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// [texto, fundo, mínimo]
export const PAIRS = [
  ["branco", "azul-500", 4.5],
  ["branco", "vermelho-500", 4.5],
  ["tinta", "branco", 4.5],
  ["tinta", "fundo", 4.5],
  ["neutro-500", "branco", 4.5],
  ["neutro-500", "fundo", 4.5],
  ["azul-600", "branco", 4.5],
  ["azul-700", "azul-100", 4.5],
  ["vermelho-600", "vermelho-50", 4.5],
  ["vermelho-700", "vermelho-100", 4.5],
  ["neutro-600", "neutro-50", 4.5],
  ["sucesso-700", "sucesso-50", 4.5],
  ["aviso-700", "aviso-50", 4.5],
];
```

- [ ] **Step 5: Implementar `design-system/tokens/build.mjs`**

```js
// Gera dist/tokens.css, dist/tailwind.preset.cjs e dist/GeraldoTokens.cs a partir de tokens.json.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const quote = (f) => (/\s/.test(f) ? `'${f}'` : f);
const stack = (fonts) => fonts.map(quote).join(", ");

function flatColors(color) {
  const out = [];
  for (const [k, v] of Object.entries(color)) {
    if (typeof v === "string") out.push([k, v]);
    else for (const [step, hex] of Object.entries(v)) out.push([`${k}-${step}`, hex]);
  }
  return out;
}

const pascal = (name) => name.split("-").map((p) => p[0].toUpperCase() + p.slice(1)).join("");

function cssFile(t) {
  const lines = [":root {"];
  for (const [name, hex] of flatColors(t.color)) lines.push(`  --${name}: ${hex};`);
  lines.push(`  --font-display: ${stack(t.font.display)};`, `  --font-body: ${stack(t.font.body)};`);
  for (const [k, v] of Object.entries(t.radius)) lines.push(`  --radius-${k}: ${v};`);
  for (const [k, v] of Object.entries(t.shadow)) lines.push(`  --shadow-${k}: ${v};`);
  for (const [k, v] of Object.entries(t.size)) lines.push(`  --${k}: ${v};`);
  lines.push("}", "");
  return `/* Gerado por design-system/tokens/build.mjs. Não edite à mão. */\n${lines.join("\n")}`;
}

function presetFile(t) {
  const preset = {
    theme: {
      extend: {
        colors: t.color,
        fontFamily: { display: t.font.display, sans: t.font.body },
        borderRadius: t.radius,
        boxShadow: t.shadow,
        minHeight: { controle: t.size["altura-controle"] },
        minWidth: { controle: t.size["altura-controle"] },
        screens: t.screens,
      },
    },
  };
  return `// Gerado por design-system/tokens/build.mjs. Não edite à mão.\nmodule.exports = ${JSON.stringify(preset, null, 2)};\n`;
}

function csFile(t) {
  const hexByte = (h, i) => `0x${h.slice(1 + i * 2, 3 + i * 2).toUpperCase()}`;
  const fields = flatColors(t.color).map(
    ([name, hex]) => `        public static readonly Color32 ${pascal(name)} = new Color32(${hexByte(hex, 0)}, ${hexByte(hex, 1)}, ${hexByte(hex, 2)}, 0xFF);`,
  );
  return `// Gerado por design-system/tokens/build.mjs. Não edite à mão.\nusing UnityEngine;\n\nnamespace Geraldo\n{\n    public static class GeraldoTokens\n    {\n${fields.join("\n")}\n    }\n}\n`;
}

export function build(tokens, outDir) {
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "tokens.css"), cssFile(tokens));
  writeFileSync(join(outDir, "tailwind.preset.cjs"), presetFile(tokens));
  writeFileSync(join(outDir, "GeraldoTokens.cs"), csFile(tokens));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const here = dirname(fileURLToPath(import.meta.url));
  const tokens = JSON.parse(readFileSync(join(here, "tokens.json"), "utf8"));
  build(tokens, join(here, "..", "dist"));
  console.log("tokens gerados em design-system/dist/");
}
```

- [ ] **Step 6: Rodar os testes e ver passar**

Run: `(cd design-system && node --test)`
Expected: todos passam. Se algum par de contraste falhar, o teste mostra a razão exata; troque o token do componente (não o limite) e avise o Vieira.

- [ ] **Step 7: Gerar `dist/` e commit**

```bash
node design-system/tokens/build.mjs
git add design-system
git commit -m "feat: tokens do design system (css, preset do Tailwind e Unity)"
git push
```

Avise o Vieira: "tokens v0 prontos em `design-system/dist/`".

---

### Task 6: Guia de referência do design system (`DESIGN_SYSTEM.md`)

> **Já feito em 08/11/2026 (direto na `main`):** `design-system/DESIGN_SYSTEM.md`, `tools/tests/test_design_system_doc.py` e, além do plano, a prévia visual `design-system/preview.html` e `preview.png`.

**Files:**
- Create: `design-system/DESIGN_SYSTEM.md`
- Test: `tools/tests/test_design_system_doc.py`

**Interfaces:**
- Consumes: `design-system/tokens/tokens.json` (Tarefa 5) e a spec do design system.
- Produces: o guia que as pessoas e as IAs leem antes de mexer na interface: as 9 regras de ouro no começo, como usar os tokens e a lista de componentes. Toda cor em hex citada no guia precisa existir em `tokens.json`.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Create `tools/tests/test_design_system_doc.py`:

```python
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "design-system/DESIGN_SYSTEM.md"
TOKENS = ROOT / "design-system/tokens/tokens.json"

COMPONENTS = [
    "PriorityBadge", "StatusBadge", "StatCard", "RobotStatusCard", "DeliveryQueueRow",
    "StockLevelBar", "MovementLogRow", "AlertBanner", "TelemetryPanel", "RequestForm",
]


def token_hexes() -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", node):
            found.add(node.upper())
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(json.loads(TOKENS.read_text(encoding="utf-8")))
    return found


def test_doc_starts_with_the_nine_golden_rules():
    text = DOC.read_text(encoding="utf-8")
    section = text.split("## Regras de ouro")[1].split("\n## ")[0]
    assert len(re.findall(r"^\d+\. ", section, re.M)) == 9


def test_every_hex_in_the_doc_exists_in_the_tokens():
    text = DOC.read_text(encoding="utf-8")
    hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", text)}
    assert hexes, "o guia deveria citar ao menos as cores principais"
    assert hexes <= token_hexes(), f"cores fora dos tokens: {hexes - token_hexes()}"


def test_doc_points_to_the_sources_of_truth():
    text = DOC.read_text(encoding="utf-8")
    for needle in ("tokens.json", "build.mjs", "tailwind.preset.cjs", "tokens.css", "GeraldoTokens.cs"):
        assert needle in text, needle


def test_doc_lists_every_domain_component():
    text = DOC.read_text(encoding="utf-8")
    missing = [c for c in COMPONENTS if c not in text]
    assert not missing, missing
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tools/tests/test_design_system_doc.py -q`
Expected: FAIL (o guia não existe).

- [ ] **Step 3: Escrever o guia**

Create `design-system/DESIGN_SYSTEM.md`:

````markdown
# Design system do G.E.R.A.L.D.O.

Guia de referência para pessoas e IAs. A especificação completa (todas as tabelas) está em
`docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md`; os valores vivem em
`design-system/tokens/tokens.json`, que é a **fonte única**.

Direção: clínica, limpa e confiável. Base branca, azul e vermelha. Cards brancos de 16 px sobre fundo claro;
a hierarquia vem de tamanho e peso, não de cor.

## Regras de ouro

1. **Sem hex solto.** Cor sempre via token (classe do preset ou `var(--azul-500)`). Exceção: SVG e canvas, importando de `tokens.css` ou do JS gerado.
2. **Vermelho só para:** prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro. Nunca para decoração nem para ação primária.
3. **Um botão primário por tela ou seção.** Os demais são secundário ou fantasma.
4. **Status nunca só por cor.** Sempre cor mais ícone ou texto.
5. **Números com `tabular-nums`** (saldo, quantidade, horário, bateria, contagens).
6. **Mobile-first.** Escreva o layout do celular primeiro e amplie com os breakpoints.
7. **Alvo de toque mínimo de 44 × 44 px** em controles (`min-h-controle`, `min-w-controle`).
8. **Texto da interface em português**, em sentence case, botão com verbo curto ("Solicitar medicamento"), sem "por favor", sem ponto final em rótulos e títulos. Mensagem de erro diz o que houve e o que fazer.
9. **Nada de valores soltos de espaçamento:** só a escala de 4 px do Tailwind.

## De onde vêm os valores

| Arquivo | Para quê |
|---|---|
| `design-system/tokens/tokens.json` | Fonte única (edite só este) |
| `design-system/tokens/build.mjs` | Gera os três arquivos de `dist/` |
| `design-system/dist/tokens.css` | Variáveis CSS (`--azul-500`, `--radius-card`, `--shadow-card`...) |
| `design-system/dist/tailwind.preset.cjs` | Preset do Tailwind (cores, fontes, raios, sombras, breakpoints) |
| `design-system/dist/GeraldoTokens.cs` | Cores `Color32` para o Unity |

Depois de editar `tokens.json`: `node design-system/tokens/build.mjs && (cd design-system && node --test)`. Ninguém edita `dist/` à mão.

## Cores principais

| Papel | Token | Hex |
|---|---|---|
| Primária (ação, item ativo) | `azul-500` | `#3A66E8` |
| Alerta clínico | `vermelho-500` | `#D92D3A` |
| Fundo das telas | `fundo` | `#F4F6FB` |
| Texto principal | `tinta` | `#1B2233` |

Escalas completas de azul, vermelho, neutro, sucesso e aviso: no `tokens.json` e na spec.

## Prioridade, status e estoque

- **Prioridade:** `critica` = vermelho, `media` = azul, `rotina` = cinza. Nunca use âmbar para prioridade.
- **Status da entrega:** `PENDENTE_APROVACAO` (aviso), `NA_FILA` (neutro), `EM_ROTA` e `AGUARDANDO_RECEBIMENTO` (azul), `ENTREGUE` (sucesso), `CANCELADA` (neutro, riscado), `FALHOU` (vermelho). Sempre com ícone e texto.
- **Estoque:** acima de 120% do mínimo = azul; entre 100% e 120% = aviso; abaixo do mínimo = vermelho com o texto "Abaixo do mínimo".

## Forma

Cards `rounded-card` (16 px) com borda `border-neutro-100` e `shadow-card`; botões, campos e linhas de lista `rounded-controle` (12 px); selos `rounded-full`. Fontes: `font-display` (Plus Jakarta Sans) para títulos e números grandes; `font-sans` (Inter) para o resto.

## Componentes

**Base:** `Button` (primário, secundário, fantasma, perigo), `Input`/`Select`/`Textarea`, `Card`, `Badge`, `Tabs`, `Table`, `Dialog`, `Toast`, `EmptyState`, `Skeleton`, `Sidebar`/`BottomNav`/`TopBar`/`PageHeader`.

**De domínio:** `PriorityBadge`, `StatusBadge`, `StatCard`, `RobotStatusCard`, `DeliveryQueueRow`, `StockLevelBar`, `MovementLogRow`, `AlertBanner`, `TelemetryPanel`, `RequestForm`.

A especificação de cada um está na seção 10 e 11 da spec do design system. A implementação web fica em `web/src/components/`.

## Navegação

Abaixo de 768 px: barra inferior com 3 a 4 itens. A partir de 768 px: barra lateral de ícones de 72 px com o item ativo destacado. Conteúdo com no máximo 1280 px.

## Testes

`(cd design-system && node --test)` confere que os tokens geram os arquivos certos e que todos os pares de texto e fundo usados nos componentes passam de 4,5:1 de contraste.
````

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tools/tests/test_design_system_doc.py -q`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add design-system/DESIGN_SYSTEM.md tools/tests/test_design_system_doc.py
git commit -m "docs: guia de referencia do design system"
git push
```
