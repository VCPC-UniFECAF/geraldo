# Semana 3, plano 1: contrato do estop e robô a 3 m/s — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar o contrato do estop pelo painel e entregar o robô da semana 3: 3,0 m/s sempre, desaceleração em curvas, obstáculos reais na telemetria, estop do backend no dispatcher, câmera RGB-D, script e roteiro da demo, e as medições a 3 m/s na simulação.

**Architecture:** O contrato (`docs/contracts/`) muda primeiro (Task 1). Depois, o `geraldo_dispatcher` ganha funções puras testadas sem ROS (`curves.py`, `obstacles.py`, junção das fontes de emergência em `emergency.py`) e adapters finos no `node.py` e no `curve_node.py`; o Nav2 e o URDF são reconfigurados para 3,0 m/s e o URDF ganha a câmera. As últimas tarefas rodam a simulação para medir e varrer os 10 pontos.

**Tech Stack:** Python 3.12, pytest, ROS 2 Jazzy (Nav2 MPPI, `nav2_msgs/SpeedLimit`), Gazebo Harmonic 8, xacro, PyYAML.

**Spec:** `docs/superpowers/specs/2026-11-13-semana3-completa-design.md` (seções 3, 5, 6, 7 e 8). Branch de execução: `feat/semana3-robo`, criada a partir de `docs/semana3-spec-planos`. Este é o plano 1 de 4 (os planos 2, 3 e 4 consomem o contrato da Task 1).

## Global Constraints

- **AGENTS.md:** contrato primeiro; nenhum segredo no repositório; nada direto na `main`; todo código novo com teste; texto de interface em português; padrões em `docs/padroes-de-projeto.md` (injeção pelo construtor, Strategy/Factory no lugar de `if/elif` por tipo, funções puras).
- **Commits:** em português, `tipo: o que mudou`, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Descrições de PR terminam com `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **ROS e Gazebo:** todo comando de simulação com `ROS_DOMAIN_ID=77` e `GZ_PARTITION=verif` (outra sessão pode estar rodando; não a toque). Nunca `pkill -f` nem `pgrep -f` (derrubam o próprio shell): usar PID. `gz sim` e o dispatcher exigem `kill -9`.
- **Git:** nunca `git stash` solto; caminhos absolutos do worktree; nada de `push` nem de PR sem o líder.
- **Design system (web e app):** sem hex solto; vermelho só para prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro; um botão primário por tela; alvo de toque mínimo de 44 px; números com `tabular-nums`; ícones `lucide-react`; texto em português, *sentence case*.
- **Backend:** JWT só HS256, exigindo `exp`, `sub`, `role` e `jti`; segredo em `GERALDO_JWT_SECRET`; estoque só por `Movimentacao`; prioridade `critica` < `media` < `rotina`, FIFO por `id`; mensagens de erro em português no formato "o que houve + o que fazer".
- **Versões:** Python 3.12 (3.11+ no backend), ROS 2 Jazzy, Gazebo Harmonic 8, Node 24, React 19, Vite 8, Tailwind v3, Electron (última estável de pelo menos 2 semanas).

Valores deste plano que valem para todas as tarefas: velocidade de cruzeiro **3,0 m/s** para qualquer prioridade; inflação do costmap local **0,55 m** (`critica`) e **0,70 m** (`media`, `rotina`); `a_lat` das curvas **1,0 m/s²**; estop do backend consultado a cada **1 s**; `obstacles` com no máximo **20** itens `{x, y, radius}` em metros no referencial `map`; backend em `http://127.0.0.1:8000`.

## Como rodar os testes (valem em todas as tarefas)

Todos os comandos partem da **raiz do worktree de execução** (a pasta que contém `AGENTS.md`).

- Raiz e scripts: `python3 -m pytest tools robot -q`
- Pacote do dispatcher (precisa do ROS carregado): `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q)`
- Pacote da descrição (idem): `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q)`

Estado de partida (confira antes da Task 1): 197 testes na raiz, 67 no dispatcher e 28 na descrição, todos verdes.

## Receita de simulação (usada nas Tasks 7, 9 e 10)

```bash
export ROS_DOMAIN_ID=77 GZ_PARTITION=verif
source /opt/ros/jazzy/setup.bash
cd <raiz do worktree>/robot/ros2_ws && colcon build --symlink-install && source install/setup.bash && cd ../..
setsid ros2 launch geraldo_description sim.launch.py headless:=true > "${TMPDIR:-/tmp}/geraldo-sim.log" 2>&1 &
echo $! > "${TMPDIR:-/tmp}/geraldo-sim.pid"
bash robot/scripts/wait_for.sh "timeout 5 ros2 topic echo --once /scan" 120
setsid ros2 launch geraldo_nav nav.launch.py > "${TMPDIR:-/tmp}/geraldo-nav.log" 2>&1 &
echo $! > "${TMPDIR:-/tmp}/geraldo-nav.pid"
bash robot/scripts/wait_for.sh "ros2 lifecycle get /amcl | grep -q '^active' && ros2 lifecycle get /bt_navigator | grep -q '^active'" 180
```

- O `setsid` faz o PID ser também o grupo do processo, então `kill -9 -- -$(cat "${TMPDIR:-/tmp}/geraldo-sim.pid")` derruba o `ros2 launch` e o `gz sim` filho (o `gz sim` só morre com `-9`). Faça o mesmo com `geraldo-nav.pid` e, quando existir, `geraldo-dispatcher.pid` e `geraldo-api.pid`. Nunca `pkill -f` nem `pgrep -f`; não toque processos que você não iniciou (outra sessão pode usar a máquina; por isso o domínio 77 e a partição `verif`).
- Rode `ps -eo pid,pgid,cmd | grep -E "gz sim|ros2 launch"` só para conferir que o que sobrou é seu.
- Depois de mudar qualquer pacote ROS, rode de novo o `colcon build --symlink-install`.

## Mapa de arquivos

| Arquivo | Task | Responsabilidade |
|---|---|---|
| `docs/contracts/openapi.yaml` | 1 | `POST`/`GET /robot/estop`, schema `EstopState`, `obstacles` com `maxItems: 20` |
| `docs/contracts/ros-interfaces.md`, `docs/contracts/robot-protocol.md` | 1, 2 | tópicos novos, estop do backend, regra de junção, formato de `obstacles`, velocidade única |
| `tools/tests/test_contracts.py` | 1, 2 | trava o contrato novo |
| `robot/scripts/openapi_check.py`, `contract_examples.py` + `docs/contracts/examples/*.json` | 1, 6 | validador com `maxItems`; exemplos regenerados com obstáculo |
| `geraldo_dispatcher/profiles.py` | 2 | perfis só com o raio de inflação |
| `robot/scripts/make_nav2_params.py` + `geraldo_nav/config/nav2_params.yaml` | 3 | 3,0 m/s, janela de 18 m e ajuste do MPPI (o YAML é gerado) |
| `geraldo_description/urdf/geraldo.urdf.xacro`, `config/bridge.yaml` | 3, 7 | teto do plugin de movimento em 3,0 m/s; câmera RGB-D e ponte |
| `geraldo_dispatcher/curves.py`, `curve_node.py`, `geraldo_nav/launch/nav.launch.py` | 4 | `curve_speed_limit` (pura) e o nó `curve_limiter` |
| `geraldo_dispatcher/obstacles.py`, `telemetry.py`, `node.py` | 5 | `StaticMap`, `detect_obstacles` e a telemetria com obstáculos |
| `geraldo_dispatcher/emergency.py`, `ports.py`, `api.py`, `robot/scripts/fake_backend.py` | 6 | junção das fontes de emergência, `estop_active` no backend |
| `robot/scripts/demo.sh`, `docs/demo-roteiro.md`, `.vscode/tasks.json`, `robot/AGENTS.md` | 8 | demo, roteiro, correção do `grep` e regras novas do robô |
| `robot/scripts/measure_speed.py`, `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md` | 9 | medição a 3 m/s e relatório |

## Achados que moldam o plano (ensaio de 13/11/2026 na simulação)

1. Só subir `vx_max` para 3,0 **não** faz o robô andar a 3 m/s: com a janela de 3 m do costmap local o MPPI (horizonte de 2,8 s) fica preso em uns 0,5 m/s, porque a trajetória a 3 m/s não cabe na janela. Com a janela de 18 m, `prune_distance` 9,0, `vx_std` 0,5 e os críticos de caminho olhando mais longe (valores da Task 3), o robô chegou a 3,0 m/s no corredor reto. A estabilidade nas portas e curvas **não** foi confirmada: é o que as Tasks 9 e 10 verificam.
2. O robô que começa virado para o lado contrário da meta **dá ré** (até -0,35 m/s) em vez de girar. Nas medições, comece sempre com o robô na base (cenário `base` do script da Task 9).
3. O Nav2 `route_server` também aparece como publicador de `/speed_limit`; o `curve_limiter` é o único que o robô usa.

---

### Task 1: Contrato do estop, telemetria com obstáculos e tópicos novos

**Files:**
- Modify: `docs/contracts/openapi.yaml`
- Modify: `docs/contracts/ros-interfaces.md`
- Modify: `docs/contracts/robot-protocol.md`
- Modify: `robot/scripts/openapi_check.py`
- Modify: `robot/scripts/contract_examples.py`
- Regenerate: `docs/contracts/examples/robot-telemetry.json` e `docs/contracts/examples/robot-events.json`
- Test: `tools/tests/test_contracts.py`, `robot/scripts/tests/test_contract_examples.py`

**Interfaces:**
- Consumes: nada (primeira tarefa).
- Produces (os planos 2, 3 e 4 dependem destes nomes):
  - `POST /robot/estop` (papéis `admin` e `farmaceutico`; corpo `EstopState`; respostas `204`, `401`, `403`, `422`) e `GET /robot/estop` (papel `robo`; `200` com `EstopState`; `401`, `403`).
  - Schema `EstopState` = `{active: boolean}`, `active` obrigatório; o backend começa com `active: false`.
  - `Telemetry.obstacles`: lista de no máximo 20 itens `{x: number, y: number, radius: number}` (todos obrigatórios), metros, referencial `map`.
  - `validate(value, schema, spec, path="$") -> list[str]` em `robot/scripts/openapi_check.py` passa a entender `maxItems` (mensagem `"$.obstacles: 21 itens, no máximo 20"`).
  - O exemplo `A_CAMINHO` de `robot-telemetry.json` passa a ter `"obstacles": [{"x": 23.0, "y": 29.0, "radius": 1.0}]`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tools/tests/test_contracts.py`, aplique o diff (acrescenta as duas operações novas à lista esperada e quatro testes ao final):

```diff
--- a/tools/tests/test_contracts.py
+++ b/tools/tests/test_contracts.py
@@ -21,4 +21,6 @@
     ("post", "/robot/events"),
     ("post", "/robot/telemetry"),
+    ("post", "/robot/estop"),
+    ("get", "/robot/estop"),
     ("get", "/telemetry"),
 }
@@ -77,2 +79,40 @@
     operation = load()["paths"]["/deliveries/{id}"]["get"]
     assert "robo" in operation["description"] and "somente leitura" in operation["description"]
+
+
+def test_estop_is_set_by_the_panel_and_read_by_the_robot():
+    spec = load()
+    path = spec["paths"]["/robot/estop"]
+    assert "admin" in path["post"]["description"] and "farmaceutico" in path["post"]["description"]
+    assert "robo" in path["get"]["description"]
+    assert set(path["post"]["responses"]) == {"204", "401", "403", "422"}
+    assert set(path["get"]["responses"]) == {"200", "401", "403"}
+    state = {"$ref": "#/components/schemas/EstopState"}
+    assert path["post"]["requestBody"]["content"]["application/json"]["schema"] == state
+    assert path["get"]["responses"]["200"]["content"]["application/json"]["schema"] == state
+    schema = spec["components"]["schemas"]["EstopState"]
+    assert schema["required"] == ["active"] and schema["properties"]["active"]["type"] == "boolean"
+
+
+def test_telemetry_obstacles_are_at_most_20_circles():
+    obstacles = load()["components"]["schemas"]["Telemetry"]["properties"]["obstacles"]
+    assert obstacles["maxItems"] == 20
+    assert obstacles["items"]["required"] == ["x", "y", "radius"]
+
+
+def test_ros_interfaces_says_who_reads_the_estop_and_what_the_bridge_may_touch():
+    text = (ROOT / "docs/contracts/ros-interfaces.md").read_text(encoding="utf-8")
+    assert "GET /robot/estop" in text
+    bridge = next(line for line in text.splitlines() if line.startswith("- `geraldo_bridge`"))
+    for topic in ("/geraldo/estop", "/geraldo/state", "/geraldo/battery", "/amcl_pose", "/plan", "/scan", "/range/*"):
+        assert topic in bridge, topic
+    for topic in ("/camera/color/image_raw", "/camera/depth/image_raw", "/speed_limit"):
+        assert topic in text, topic
+
+
+def test_robot_protocol_fixes_the_estop_cadence_the_join_rule_and_the_obstacles_format():
+    text = (ROOT / "docs/contracts/robot-protocol.md").read_text(encoding="utf-8")
+    assert "`GET /robot/estop` a cada 1 s" in text
+    assert "só sai da parada com as duas fontes desligadas" in text
+    assert "até 20 itens `{x, y, radius}`" in text
+    assert "sempre `[]`" not in text
```

Em `robot/scripts/tests/test_contract_examples.py`, acrescente ao final:

```python


def test_the_moving_example_shows_an_obstacle_and_the_validator_caps_the_list_at_20():
    assert telemetry_examples()["A_CAMINHO"]["obstacles"] == [{"x": 23.0, "y": 29.0, "radius": 1.0}]
    too_many = {**TELEMETRY, "obstacles": [{"x": 1.0, "y": 2.0, "radius": 0.3}] * 21}
    assert any("no máximo 20" in e for e in validate(too_many, SCHEMAS["Telemetry"], SPEC))
    assert validate({**TELEMETRY, "obstacles": [{"x": 1.0, "y": 2.0}]}, SCHEMAS["Telemetry"], SPEC) == [
        "$.obstacles[0]: falta radius"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tools/tests/test_contracts.py robot/scripts/tests/test_contract_examples.py -q`
Expected: FAIL (`test_all_contract_operations_are_declared`, `KeyError: '/robot/estop'`, falta `"no máximo 20"`, exemplo `A_CAMINHO` sem obstáculo, e os testes dos `.md`).

- [ ] **Step 3: Contrato OpenAPI**

Aplique em `docs/contracts/openapi.yaml`:

```diff
--- a/docs/contracts/openapi.yaml
+++ b/docs/contracts/openapi.yaml
@@ -220,4 +220,32 @@
         '403': { $ref: '#/components/responses/Forbidden' }
         '422': { description: Corpo inválido (estado fora do enum, bateria fora de 0 a 100) }
+  /robot/estop:
+    post:
+      summary: O painel aciona ou libera a parada de emergência do robô
+      description: >
+        Papéis admin e farmaceutico. O backend guarda o último valor (começa em active false) e o devolve no GET /robot/estop.
+        Com active true o robô para e o estado vira PARADA_EMERGENCIA; ele só volta a andar quando esta fonte e o tópico
+        /geraldo/estop estiverem desligados (ver docs/contracts/robot-protocol.md).
+      requestBody:
+        required: true
+        content:
+          application/json:
+            schema: { $ref: '#/components/schemas/EstopState' }
+      responses:
+        '204': { description: Parada de emergência atualizada }
+        '401': { $ref: '#/components/responses/Unauthorized' }
+        '403': { $ref: '#/components/responses/Forbidden' }
+        '422': { description: Corpo inválido (active ausente ou não booleano) }
+    get:
+      summary: O robô consulta se a parada de emergência do painel está acionada
+      description: Papel robo, a cada 1 s (ver docs/contracts/robot-protocol.md).
+      responses:
+        '200':
+          description: Estado da parada de emergência
+          content:
+            application/json:
+              schema: { $ref: '#/components/schemas/EstopState' }
+        '401': { $ref: '#/components/responses/Unauthorized' }
+        '403': { $ref: '#/components/responses/Forbidden' }
   /telemetry:
     get:
@@ -377,4 +405,9 @@
         quantity: { type: integer, minimum: 1 }
         created_at: { type: string, format: date-time }
+    EstopState:
+      type: object
+      required: [active]
+      properties:
+        active: { type: boolean, description: "true = parada de emergência acionada" }
     Telemetry:
       type: object
@@ -402,6 +435,9 @@
         obstacles:
           type: array
+          maxItems: 20
+          description: Círculos {x, y, radius} em metros no referencial map, os mais próximos do robô primeiro
           items:
             type: object
+            required: [x, y, radius]
             properties:
               x: { type: number }
```

- [ ] **Step 4: Contrato ROS**

Aplique em `docs/contracts/ros-interfaces.md`:

```diff
--- a/docs/contracts/ros-interfaces.md
+++ b/docs/contracts/ros-interfaces.md
@@ -20,7 +20,12 @@
 | `/geraldo/state` | `std_msgs/msg/String` | estado da máquina de estados | 2 |
 | `/geraldo/battery` | `sensor_msgs/msg/BatteryState` | bateria | 2 |
-| `/geraldo/estop` | `std_msgs/msg/Bool` | quem aciona → `geraldo_dispatcher` (`true` para, `false` libera) | 2 |
+| `/geraldo/estop` | `std_msgs/msg/Bool` | quem aciona → `geraldo_dispatcher` (`true` para, `false` libera); soma-se à consulta `GET /robot/estop` ao backend | 2 |
+| `/amcl_pose` | `geometry_msgs/msg/PoseWithCovarianceStamped` | Nav2 (AMCL) → `geraldo_dispatcher` e `geraldo_bridge` | 3 |
+| `/plan` | `nav_msgs/msg/Path` | Nav2 → `geraldo_dispatcher`, `curve_limiter` e `geraldo_bridge` | 3 |
+| `/speed_limit` | `nav2_msgs/msg/SpeedLimit` | `curve_limiter` → Nav2 (limite absoluto em m/s; só esse nó publica) | 3 |
 
 Não há sensor a 180° (a traseira fica livre para o painel de manutenção).
+
+A câmera RGB-D fica na frente do robô e só publica as duas imagens acima (a ponte Gazebo → ROS as leva ao ROS). Nenhum nó lê marcador nelas.
 
 `/scan` cobre cerca de 172° à frente: o baú bloqueia a traseira. A traseira é coberta pelos sensores `/range/rear_*` (semana 2).
@@ -30,4 +35,7 @@
 - Navegação: ação `NavigateToPose` do Nav2 (`nav2_msgs/action/NavigateToPose`).
 - `geraldo_dispatcher` (Samuel): chama `POST /robot/next-task`, converte `origin_waypoint` e `dest_waypoint` em poses usando `waypoints.yaml`, envia as metas ao Nav2 e reporta `POST /robot/events`.
+- `geraldo_dispatcher` também lê o estado da parada de emergência do backend (`GET /robot/estop`, papel `robo`, a cada 1 s) e o junta com o tópico `/geraldo/estop`: com qualquer fonte ligada o robô para, e só sai da parada com as duas fontes desligadas (detalhes em `robot-protocol.md`).
+- `curve_limiter` (Samuel): lê `/plan` e `/amcl_pose` e publica em `/speed_limit` a velocidade máxima que a curvatura à frente permite.
+- `geraldo_bridge` (app, semana 3): publica/assina só `/geraldo/estop`, `/geraldo/state`, `/geraldo/battery`, `/amcl_pose`, `/plan`, `/scan` e `/range/*`. Nunca `/cmd_vel`.
 - `waypoints.yaml`: `waypoints: { <id>: { room, x, y, yaw } }`, com `yaw` em graus.
 
```

- [ ] **Step 5: Protocolo do robô**

Aplique em `docs/contracts/robot-protocol.md` (obstáculos, seção 5 de emergência reescrita e as tarefas de cada frente na seção 7):

```diff
--- a/docs/contracts/robot-protocol.md
+++ b/docs/contracts/robot-protocol.md
@@ -42,5 +42,5 @@
 - `POST /robot/telemetry` a cada 1 s, corpo `Telemetry` (`204` na resposta). Sem pose do AMCL ainda, o robô não envia.
 - `route`: no máximo 50 pontos, tirados do `/plan` do Nav2 (vazia quando parado).
-- `obstacles`: **sempre `[]` por enquanto** (o robô ainda não detecta obstáculos por conta própria).
+- `obstacles`: até 20 itens `{x, y, radius}`, em metros, no referencial `map` (um círculo por grupo de pontos do LiDAR). O robô leva o `/scan` para o `map` pela pose do AMCL, descarta o que coincide com o mapa estático (tolerância de 0,25 m), agrupa os pontos que estão a menos de 0,35 m um do outro e envia os grupos mais próximos do robô primeiro. Lista vazia quando não há nada novo à vista.
 - `battery`: virtual (gasta andando, gasta pouco esperando, recarrega parado na base), de 0 a 100.
 - `delivery_id`: a entrega em curso, `null` em `IDLE`.
@@ -49,5 +49,10 @@
 ## 5. Emergência
 
-`/geraldo/estop` (`std_msgs/Bool`) é tópico ROS, não HTTP. Com `true`, o robô cancela a meta, para e o estado vira `PARADA_EMERGENCIA` em cerca de 1 s (a telemetria acompanha). Com `false`, volta ao estado anterior e refaz a mesma meta. Botão no painel exige contrato novo (semana 3).
+Há duas fontes de parada, e o robô as junta:
+
+1. O tópico ROS `/geraldo/estop` (`std_msgs/Bool`), para quem está na máquina.
+2. O backend: o painel chama `POST /robot/estop` com `{"active": true}` (papéis `admin` e `farmaceutico`) e o robô consulta `GET /robot/estop` (papel `robo`, resposta `{"active": bool}`). O backend começa com `active` falso. `GET /robot/estop` a cada 1 s, com o mesmo login do robô.
+
+Regra de junção: com **qualquer** fonte ligada, o robô cancela a meta, para e o estado vira `PARADA_EMERGENCIA` (a telemetria acompanha, em até uns 2 s no caso do backend); só sai da parada com as duas fontes desligadas, e então volta ao estado anterior e refaz a mesma meta. Se a consulta ao backend falhar, vale o último valor conhecido: não libera nem aciona sozinho.
 
 ## 6. Resiliência
@@ -66,9 +71,11 @@
 4. `POST /robot/next-task` deve pular `rotina` fora da janela de baixo pico: o robô não consegue devolver uma tarefa que o backend já marcou `EM_ROTA`.
 5. Locais sem `waypoint` (a recepção) não podem ser origem nem destino: recusar na criação da entrega (já está no seu plano). Se uma passar, o robô manda `FAILED` e não se mexe.
+6. `POST /robot/estop` (papéis `admin` e `farmaceutico`) guarda `{active}` em memória (começa em `false`) e `GET /robot/estop` (papel `robo`) devolve o último valor; `422` se o corpo não tiver `active` booleano.
 
 **Vieira (web)**
 1. Montar o MSW e as telas de estado do robô com `examples/robot-telemetry.json` (um corpo por estado) em vez de inventar fixtures.
 2. "Confirmar recebimento" só faz sentido com `status = AGUARDANDO_RECEBIMENTO`; o estado do robô nessa hora é `AGUARDANDO_RETIRADA`.
-3. `obstacles` vem vazio e `route` pode vir vazio.
+3. `obstacles` traz até 20 círculos `{x, y, radius}` em metros no referencial `map` (pode vir vazio) e `route` também pode vir vazia.
+4. Botão de emergência: `POST /robot/estop` com `{active: true}`; o estado `PARADA_EMERGENCIA` na telemetria confirma (em até uns 2 s). Para liberar, `{active: false}`: se o tópico ROS ainda estiver ligado, o robô continua parado.
 
 **Pedro (qualidade)**
@@ -76,2 +83,3 @@
 2. O teste de contrato precisa incluir a operação `POST /robot/telemetry` (nova no OpenAPI) na lista de pendentes até o Erik implementar.
 3. O ataque "obstáculo falso na telemetria" mira `POST /robot/telemetry`; as mitigações são papel `robo`, estado no enum, bateria de 0 a 100 e `updated_at` ignorado.
+4. `tools/mock_robot.py` também consulta `GET /robot/estop` a cada 1 s e fica em `PARADA_EMERGENCIA` enquanto vier `true`; o teste de contrato inclui `POST` e `GET /robot/estop`.
```

- [ ] **Step 6: Validador e exemplos**

Aplique em `robot/scripts/openapi_check.py`:

```diff
--- a/robot/scripts/openapi_check.py
+++ b/robot/scripts/openapi_check.py
@@ -1,5 +1,5 @@
 """Validador mínimo de corpos contra os schemas do docs/contracts/openapi.yaml (sem dependência nova).
 
-Cobre só o que o contrato usa: $ref, nullable, enum, type, format date-time, minimum, maximum, required, properties e items.
+Cobre só o que o contrato usa: $ref, nullable, enum, type, format date-time, minimum, maximum, maxItems, required, properties e items.
 """
 from datetime import datetime
@@ -39,4 +39,6 @@
                 errors += validate(value[name], sub, spec, f"{path}.{name}")
     if kind == "array":
+        if "maxItems" in schema and len(value) > schema["maxItems"]:
+            errors.append(f"{path}: {len(value)} itens, no máximo {schema['maxItems']}")
         for index, item in enumerate(value):
             errors += validate(item, schema.get("items", {}), spec, f"{path}[{index}]")
```

Aplique em `robot/scripts/contract_examples.py` (cada estado agora carrega também a lista de obstáculos; só `A_CAMINHO` tem um):

```diff
--- a/robot/scripts/contract_examples.py
+++ b/robot/scripts/contract_examples.py
@@ -32,13 +32,13 @@
 TASK = {"id": DELIVERY_ID, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega", "priority": "media"}
 
-# estado: (pose, bateria, entrega em curso, rota)
+# estado: (pose, bateria, entrega em curso, rota, obstáculos (x, y, raio))
 SNAPSHOTS = {
-    State.IDLE: (Pose(6.5, 26.5, -1.5708), 100.0, None, []),
-    State.CARREGANDO: (Pose(7.0, 24.0, -1.5708), 99.8, DELIVERY_ID, []),
-    State.A_CAMINHO: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, [(14.2, 28.9), (20.0, 28.9), (29.0, 28.9)]),
-    State.CHEGOU: (Pose(14.5, 4.0, -1.5708), 98.0, DELIVERY_ID, []),
-    State.AGUARDANDO_RETIRADA: (Pose(14.5, 4.0, -1.5708), 97.9, DELIVERY_ID, []),
-    State.VOLTANDO: (Pose(10.0, 28.9, 3.1416), 97.0, DELIVERY_ID, [(10.0, 28.9), (6.5, 26.5)]),
-    State.PARADA_EMERGENCIA: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, []),
+    State.IDLE: (Pose(6.5, 26.5, -1.5708), 100.0, None, [], []),
+    State.CARREGANDO: (Pose(7.0, 24.0, -1.5708), 99.8, DELIVERY_ID, [], []),
+    State.A_CAMINHO: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, [(14.2, 28.9), (20.0, 28.9), (29.0, 28.9)], [(23.0, 29.0, 1.0)]),
+    State.CHEGOU: (Pose(14.5, 4.0, -1.5708), 98.0, DELIVERY_ID, [], []),
+    State.AGUARDANDO_RETIRADA: (Pose(14.5, 4.0, -1.5708), 97.9, DELIVERY_ID, [], []),
+    State.VOLTANDO: (Pose(10.0, 28.9, 3.1416), 97.0, DELIVERY_ID, [(10.0, 28.9), (6.5, 26.5)], []),
+    State.PARADA_EMERGENCIA: (Pose(14.2, 28.9, 0.0), 99.1, DELIVERY_ID, [], []),
 }
 # cenário: (statuses da entrega que o backend devolve, a origem é inalcançável?)
@@ -75,6 +75,6 @@
 
 def telemetry_examples() -> dict[str, dict]:
-    return {state.value: build_telemetry(state, pose, battery, delivery_id, route, [], NOW)
-            for state, (pose, battery, delivery_id, route) in SNAPSHOTS.items()}
+    return {state.value: build_telemetry(state, pose, battery, delivery_id, route, obstacles, NOW)
+            for state, (pose, battery, delivery_id, route, obstacles) in SNAPSHOTS.items()}
 
 
```

Regenere os exemplos e confira que só o `A_CAMINHO` mudou:

Run: `python3 robot/scripts/contract_examples.py && git diff --stat docs/contracts/examples`
Expected: `robot-telemetry.json` com 6 linhas a mais e `robot-events.json` sem mudança.

- [ ] **Step 7: Rodar e ver passar**

Run: `python3 -m pytest tools robot -q`
Expected: PASS (tudo verde, com os testes novos a mais).

- [ ] **Step 8: Commit**

```bash
git add docs/contracts tools/tests/test_contracts.py robot/scripts/openapi_check.py robot/scripts/contract_examples.py robot/scripts/tests/test_contract_examples.py
git commit -m "docs(contratos): estop pelo painel, obstaculos da telemetria e tópicos da semana 3

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Perfis de prioridade só com a inflação

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/profiles.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`
- Modify: `docs/contracts/robot-protocol.md` (seção 2)
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_profiles.py`, `tools/tests/test_contracts.py`

**Interfaces:**
- Consumes: nada de tarefas anteriores além do estado do repositório (a Task 1 já mudou `robot-protocol.md` e `test_contracts.py`).
- Produces: `NavProfile(name: str, inflation_radius: float)` (sem `max_speed`); `PROFILES: dict[str, NavProfile]` com `critica` 0,55 m, `media` 0,70 m e `rotina` 0,70 m; `DEFAULT_PROFILE = PROFILES["media"]`; `profile_for(priority: str) -> NavProfile` (levanta `ValueError("Prioridade desconhecida: ...")`, como antes). `Nav2Tuner.apply(profile)` só ajusta o `inflation_layer.inflation_radius` do costmap local; ninguém mais publica `/speed_limit` por prioridade.

- [ ] **Step 1: Escrever os testes que falham**

Em `test/test_profiles.py`, troque o teste `test_critical_is_faster_and_squeezes_closer_than_routine` por:

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/test/test_profiles.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/test/test_profiles.py
@@ -16,7 +16,7 @@
 
 
-def test_critical_is_faster_and_squeezes_closer_than_routine():
-    assert PROFILES["critica"].max_speed > PROFILES["media"].max_speed > PROFILES["rotina"].max_speed
-    assert PROFILES["critica"].inflation_radius < PROFILES["media"].inflation_radius
+def test_only_the_inflation_radius_depends_on_the_priority():
+    assert [(p.name, p.inflation_radius) for p in PROFILES.values()] == [("critica", 0.55), ("media", 0.70), ("rotina", 0.70)]
+    assert not any(hasattr(p, "max_speed") for p in PROFILES.values())  # a velocidade é 3,0 m/s para todas
 
 
```

Em `tools/tests/test_contracts.py`, acrescente ao final:

```python


def test_robot_protocol_no_longer_ties_the_speed_to_the_priority():
    text = (ROOT / "docs/contracts/robot-protocol.md").read_text(encoding="utf-8")
    assert "`critica` 1,0 m/s" not in text and "0,8 m/s" not in text and "0,5 m/s" not in text
    assert "sempre a 3,0 m/s" in text
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_profiles.py -q); python3 -m pytest tools/tests/test_contracts.py -q`
Expected: FAIL (`assert not any(hasattr(p, "max_speed") ...)` e `sempre a 3,0 m/s`).

- [ ] **Step 3: Implementar**

`geraldo_dispatcher/profiles.py` (arquivo inteiro):

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class NavProfile:
    """Como o robô navega numa prioridade: só o raio de inflação do costmap local (m). A velocidade é 3,0 m/s para todas."""

    name: str
    inflation_radius: float  # menor = passa mais perto dos obstáculos (desvio mais agressivo)


# O contrato fixa as prioridades (OpenAPI Priority). A média e a rotina usam o raio padrão do Nav2 (nav2_params.yaml).
PROFILES: dict[str, NavProfile] = {
    "critica": NavProfile("critica", inflation_radius=0.55),
    "media": NavProfile("media", inflation_radius=0.70),
    "rotina": NavProfile("rotina", inflation_radius=0.70),
}
DEFAULT_PROFILE = PROFILES["media"]


def profile_for(priority: str) -> NavProfile:
    if priority not in PROFILES:
        raise ValueError(f"Prioridade desconhecida: {priority}. Use critica, media ou rotina.")
    return PROFILES[priority]
```

`geraldo_dispatcher/ports.py` (só o texto da porta `NavigationTuner`):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py
@@ -42,3 +42,3 @@
     @abstractmethod
     def apply(self, profile: NavProfile) -> None:
-        """Aplica velocidade máxima e raio de inflação do perfil."""
+        """Aplica o raio de inflação do perfil (a velocidade não muda com a prioridade)."""
```

`geraldo_dispatcher/node.py` (o `Nav2Tuner` deixa de publicar `/speed_limit`; o `import` de `SpeedLimit` sai):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py
@@ -8,5 +8,4 @@
 from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
 from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
-from nav2_msgs.msg import SpeedLimit
 from nav_msgs.msg import Path
 from rcl_interfaces.msg import Parameter as ParameterMsg
@@ -89,12 +88,10 @@
 
 
-class Nav2Tuner(NavigationTuner):  # ADAPTER: traduz o perfil para o /speed_limit e o costmap local do Nav2
+class Nav2Tuner(NavigationTuner):  # ADAPTER: traduz o perfil para o raio de inflação do costmap local do Nav2
     def __init__(self, node: Node) -> None:
         self._node = node
-        self._speed = node.create_publisher(SpeedLimit, "/speed_limit", 10)
         self._costmap = node.create_client(SetParameters, "/local_costmap/local_costmap/set_parameters")
 
     def apply(self, profile: NavProfile) -> None:
-        self._speed.publish(SpeedLimit(percentage=False, speed_limit=profile.max_speed))
         if not self._costmap.wait_for_service(timeout_sec=2.0):
             self._node.get_logger().warning("costmap local indisponível: raio de inflação não alterado")
@@ -103,5 +100,5 @@
         request = SetParameters.Request(parameters=[ParameterMsg(name="inflation_layer.inflation_radius", value=value)])
         self._costmap.call_async(request)
-        self._node.get_logger().info(f"perfil {profile.name}: {profile.max_speed} m/s, inflação {profile.inflation_radius} m")
+        self._node.get_logger().info(f"perfil {profile.name}: inflação {profile.inflation_radius} m")
 
 
```

`docs/contracts/robot-protocol.md` (a frase da seção 2 sobre o perfil):

```diff
--- a/docs/contracts/robot-protocol.md
+++ b/docs/contracts/robot-protocol.md
@@ -23,5 +23,5 @@
 | 9 | `IDLE` | volta ao passo 1 |
 
-O perfil de navegação segue a `priority` da tarefa: `critica` 1,0 m/s, `media` 0,8 m/s, `rotina` 0,5 m/s (e raio de inflação do costmap local de 0,55 m para `critica`, 0,70 m para as outras).
+O robô anda sempre a 3,0 m/s (e desacelera sozinho nas curvas, pelo `/speed_limit` do Nav2). A `priority` da tarefa muda só o raio de inflação do costmap local: 0,55 m para `critica` e 0,70 m para `media` e `rotina`.
 
 ## 3. Falhas
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q && python3 -c "import geraldo_dispatcher.node") && python3 -m pytest tools robot -q`
Expected: PASS (sem `grep` de `SpeedLimit` ou `max_speed` em `geraldo_dispatcher/*.py`: `grep -rn "max_speed\|SpeedLimit" robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher` não imprime nada).

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher docs/contracts/robot-protocol.md tools/tests/test_contracts.py
git commit -m "refactor(robo): prioridade muda so o raio de inflacao, sem velocidade por perfil

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Velocidade de 3,0 m/s no Nav2 e no URDF

**Files:**
- Modify: `robot/scripts/make_nav2_params.py`
- Regenerate: `robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml` (arquivo gerado: não edite à mão)
- Modify: `robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`
- Test: `robot/scripts/tests/test_make_nav2_params.py`, `robot/ros2_ws/src/geraldo_description/test/test_urdf.py`

**Interfaces:**
- Consumes: nada de tarefas anteriores.
- Produces em `robot/scripts/make_nav2_params.py`: `CRUISE_SPEED = 3.0`; `LOCAL_COSTMAP_SIZE = 18` (m, largura e altura da janela do costmap local); `MPPI_TUNING = {"vx_std": 0.5, "prune_distance": 9.0}`; `CRITIC_TUNING = {"PathFollowCritic": {"offset_from_furthest": 60, "cost_weight": 15.0}, "PathAlignCritic": {"offset_from_furthest": 100}}`; `patch_params(params: dict) -> dict` aplica tudo. No URDF, `max_linear_velocity` do `DiffDrive` = 3.0. A ponte (`config/bridge.yaml`) só traduz mensagens e não limita velocidade: nada a mudar nela. O suavizador de velocidade (`velocity_smoother.max_velocity[0]`) segue o `CRUISE_SPEED` como antes; aceleração e desaceleração dele continuam 2,5 m/s² (a Task 9 mede se bastam).

- [ ] **Step 1: Escrever os testes que falham**

Em `robot/scripts/tests/test_make_nav2_params.py`, aplique o diff (importa as constantes novas, renomeia o teste de cruzeiro para 3,0 e acrescenta dois testes):

```diff
--- a/robot/scripts/tests/test_make_nav2_params.py
+++ b/robot/scripts/tests/test_make_nav2_params.py
@@ -1,3 +1,5 @@
-from robot.scripts.make_nav2_params import CRUISE_SPEED, FOOTPRINT, INITIAL_POSE, patch_params
+from robot.scripts.make_nav2_params import (
+    CRITIC_TUNING, CRUISE_SPEED, FOOTPRINT, INITIAL_POSE, LOCAL_COSTMAP_SIZE, MPPI_TUNING, patch_params,
+)
 
 
@@ -50,7 +52,7 @@
 
 
-def test_robot_cruises_at_0_8_m_s_in_both_the_controller_and_the_velocity_smoother():
+def test_robot_cruises_at_3_m_s_in_both_the_controller_and_the_velocity_smoother():
     out = patch_params(fake_defaults())
-    assert out["controller_server"]["ros__parameters"]["FollowPath"]["vx_max"] == CRUISE_SPEED == 1.0
+    assert out["controller_server"]["ros__parameters"]["FollowPath"]["vx_max"] == CRUISE_SPEED == 3.0
     assert out["velocity_smoother"]["ros__parameters"]["max_velocity"][0] == CRUISE_SPEED
 
@@ -67,2 +69,19 @@
     out = patch_params(fake_defaults())
     assert out["local_costmap"]["local_costmap"]["ros__parameters"]["plugins"] == ["voxel_layer"]
+
+
+def test_the_mppi_horizon_fits_in_the_local_costmap_and_in_the_pruned_path_at_cruise_speed():
+    horizon = CRUISE_SPEED * 56 * 0.05          # time_steps x model_dt do nav2_params padrão: 8,4 m a 3 m/s
+    out = patch_params(fake_defaults())
+    follow = out["controller_server"]["ros__parameters"]["FollowPath"]
+    local = out["local_costmap"]["local_costmap"]["ros__parameters"]
+    assert local["width"] == local["height"] == LOCAL_COSTMAP_SIZE == 18
+    assert LOCAL_COSTMAP_SIZE / 2 >= horizon     # a trajetória inteira cabe na janela (raio de 9 m)
+    assert follow["prune_distance"] == MPPI_TUNING["prune_distance"] == 9.0 and follow["prune_distance"] >= horizon
+    assert follow["vx_std"] == 0.5
+
+
+def test_the_path_critics_look_far_enough_ahead_for_cruise_speed():
+    follow = patch_params(fake_defaults())["controller_server"]["ros__parameters"]["FollowPath"]
+    assert follow["PathFollowCritic"] == CRITIC_TUNING["PathFollowCritic"] == {"offset_from_furthest": 60, "cost_weight": 15.0}
+    assert follow["PathAlignCritic"] == {"offset_from_furthest": 100}
```

Em `robot/ros2_ws/src/geraldo_description/test/test_urdf.py`, no teste `test_diff_drive_allows_the_nav2_cruise_speed_and_turn_rate`, troque a linha do `max_linear_velocity`:

```diff
--- a/robot/ros2_ws/src/geraldo_description/test/test_urdf.py
+++ b/robot/ros2_ws/src/geraldo_description/test/test_urdf.py
@@ -89,5 +89,5 @@
         p for g in robot.findall("gazebo") for p in g.findall("plugin") if p.get("filename") == "gz-sim-diff-drive-system"
     )
-    assert float(plugin.find("max_linear_velocity").text) >= 1.0     # velocidade de cruzeiro pedida ao Nav2
+    assert float(plugin.find("max_linear_velocity").text) >= 3.0     # velocidade de cruzeiro pedida ao Nav2
     assert float(plugin.find("max_angular_velocity").text) >= 1.9    # giro máximo pedido ao Nav2
 
@@ -159,2 +159,3 @@
     assert int(sensor.find("lidar/scan/horizontal/samples").text) == 5
     assert float(sensor.find("lidar/range/max").text) == pytest.approx(2.0)
+
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest robot/scripts/tests/test_make_nav2_params.py -q; source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test/test_urdf.py -q)`
Expected: FAIL (`ImportError: cannot import name 'CRITIC_TUNING'` no primeiro; `assert 1.0 >= 3.0` no segundo).

- [ ] **Step 3: Implementar**

`robot/scripts/make_nav2_params.py`:

```diff
--- a/robot/scripts/make_nav2_params.py
+++ b/robot/scripts/make_nav2_params.py
@@ -23,6 +23,17 @@
     "update_min_d": 0.1, "update_min_a": 0.1,
 }
-# m/s: antes 0,5 e depois 0,8. É o teto do plugin de movimento do URDF e ainda cabe nos corredores de 2 m e nas portas de 1 m.
-CRUISE_SPEED = 1.0
+# m/s: velocidade de cruzeiro única (pedido do líder, ~10 km/h), para qualquer prioridade. Antes 0,5, 0,8 e 1,0.
+# É também o teto do plugin de movimento do URDF. A desaceleração em curvas vem do nó curve_limiter pelo /speed_limit.
+CRUISE_SPEED = 3.0
+# O MPPI só chega à velocidade de cruzeiro se (1) a janela do costmap local cobrir o horizonte (56 passos x 0,05 s = 2,8 s,
+# ou 8,4 m a 3 m/s; com a janela de 3 m o robô não passava de uns 0,5 m/s), (2) o caminho podado for tão longo quanto o
+# horizonte e (3) os críticos de caminho olharem longe e a amostragem tiver ruído para acelerar. Valores achados na
+# simulação em 13/11/2026 (corredor reto a 3,0 m/s); a medição da Task 9 do plano 1 os confirma ou ajusta.
+LOCAL_COSTMAP_SIZE = 18      # m (largura e altura da janela do costmap local)
+MPPI_TUNING = {"vx_std": 0.5, "prune_distance": 9.0}
+CRITIC_TUNING = {
+    "PathFollowCritic": {"offset_from_furthest": 60, "cost_weight": 15.0},
+    "PathAlignCritic": {"offset_from_furthest": 100},
+}
 
 
@@ -35,5 +46,11 @@
     # como a maca do corredor norte, e o robô para na frente dela em vez de replanejar pela cruz central.
     # Validado em 12/11/2026: com a camada ligada a varredura dos 10 pontos continua em TODOS OS PONTOS OK.
-    params["controller_server"]["ros__parameters"]["FollowPath"]["vx_max"] = CRUISE_SPEED
+    follow = params["controller_server"]["ros__parameters"]["FollowPath"]
+    follow["vx_max"] = CRUISE_SPEED
+    follow.update(MPPI_TUNING)
+    for critic, values in CRITIC_TUNING.items():
+        follow.setdefault(critic, {}).update(values)
+    local = params["local_costmap"]["local_costmap"]["ros__parameters"]
+    local["width"] = local["height"] = LOCAL_COSTMAP_SIZE
     params["velocity_smoother"]["ros__parameters"]["max_velocity"][0] = CRUISE_SPEED   # senão o suavizador corta o controlador
     amcl = params["amcl"]["ros__parameters"]
```

`robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro` (no bloco do plugin `gz-sim-diff-drive-system`):

```diff
--- a/robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro
+++ b/robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro
@@ -218,5 +218,5 @@
       <frame_id>odom</frame_id>
       <child_frame_id>base_link</child_frame_id>
-      <max_linear_velocity>1.0</max_linear_velocity>
+      <max_linear_velocity>3.0</max_linear_velocity>
       <max_angular_velocity>2.0</max_angular_velocity>
     </plugin>
```

Regenere o YAML do Nav2 (precisa de `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`):

Run: `python3 robot/scripts/make_nav2_params.py && git diff --stat robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml && git diff robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml | grep '^[+-] '`
Expected: só estas linhas mudam: `vx_std` 0.2→0.5, `vx_max` 1.0→3.0, `prune_distance` 1.7→9.0, `offset_from_furthest` do `PathAlignCritic` 20→100, `cost_weight` e `offset_from_furthest` do `PathFollowCritic` 5.0→15.0 e 5→60, `width` e `height` do costmap local 3→18, e o primeiro item de `velocity_smoother.max_velocity` 1.0→3.0.

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tools robot -q && source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q) && (cd robot/ros2_ws && colcon build --symlink-install 2>&1 | tail -3)`
Expected: PASS e `Summary: 3 packages finished`.

- [ ] **Step 5: Commit**

```bash
git add robot/scripts/make_nav2_params.py robot/scripts/tests/test_make_nav2_params.py robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml robot/ros2_ws/src/geraldo_description
git commit -m "feat(robo): velocidade de cruzeiro de 3 m/s no Nav2 e no plugin de movimento

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Desaceleração em curvas (`curve_speed_limit` e o nó `curve_limiter`)

**Files:**
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/curves.py`
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/curve_node.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/setup.py`
- Modify: `robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_curves.py`, `robot/ros2_ws/src/geraldo_dispatcher/test/test_curve_launch.py`

**Interfaces:**
- Consumes: `CRUISE_SPEED = 3.0` (Task 3; o nó usa `V_MAX = 3.0` próprio, mesmo valor).
- Produces em `geraldo_dispatcher/curves.py` (funções puras, sem ROS):
  - `curve_speed_limit(path_xy: list[tuple[float, float]], v_max: float = 3.0, a_lat: float = 1.0, a_brake: float = 1.5, v_min: float = 0.3, lookahead: float = 10.0, step: float = 0.5) -> float` — o primeiro ponto de `path_xy` é a posição do robô. Em cada ponto a curva permite `sqrt(a_lat / curvatura)` (spec: `v = min(3,0; √(a_lat / curvatura))`); como é preciso frear antes da curva, o limite de agora é o menor `sqrt(v_ponto² + 2·a_brake·distância)` dentro de `lookahead`; o resultado fica entre `v_min` e `v_max`.
  - `resample(path_xy, step=0.5)`, `curvature(a, b, c) -> float` (Menger, 1/m), `remaining_path(path_xy, x, y)`; constantes `V_MAX`, `A_LAT`, `A_BRAKE`, `V_MIN`, `LOOKAHEAD`, `STEP`.
- Produces: executável ROS `curve_limiter` (pacote `geraldo_dispatcher`) que assina `/plan` (`nav_msgs/Path`) e `/amcl_pose` e publica `nav2_msgs/SpeedLimit` (`percentage=False`, em m/s) em `/speed_limit` só quando o valor muda (arredondado a 0,01); parâmetros `v_max` (3.0), `a_lat` (1.0), `a_brake` (1.5). O `nav.launch.py` o inicia com `use_sim_time`.

- [ ] **Step 1: Escrever os testes que falham**

`test/test_curves.py`:

```python
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.curves import curvature, curve_speed_limit, remaining_path, resample  # noqa: E402


def line(length, y=0.0, x0=0.0, step=0.05):
    return [(x0 + i * step, y) for i in range(int(length / step) + 1)]


def corner(before=5.0, after=5.0, step=0.05):
    """Reta de `before` m ao longo de +x seguida de uma quina de 90° e `after` m ao longo de +y."""
    first = [(i * step, 0.0) for i in range(int(before / step) + 1)]
    second = [(before, i * step) for i in range(1, int(after / step) + 1)]
    return first + second


def arc(radius, angle=math.pi / 2, step=0.05):
    n = int(radius * angle / step)
    return [(radius * math.sin(i * step / radius), radius * (1 - math.cos(i * step / radius))) for i in range(n + 1)]


def test_resample_spaces_the_points_by_arc_length_and_keeps_the_first():
    points = resample(line(2.0), step=0.5)
    assert points[0] == (0.0, 0.0) and len(points) == 5
    assert [round(x, 3) for x, _ in points] == [0.0, 0.5, 1.0, 1.5, 2.0]
    assert resample([]) == []


def test_curvature_is_the_inverse_of_the_circle_radius_and_zero_on_a_line():
    assert curvature((0, 0), (1, 0), (2, 0)) == 0.0
    assert curvature((0, 0), (1, 0), (1, 0)) == 0.0
    r = 2.0
    pts = [(r * math.sin(t), r * (1 - math.cos(t))) for t in (0.0, 0.3, 0.6)]
    assert curvature(*pts) == pytest.approx(1 / r)


def test_a_straight_corridor_allows_the_full_speed():
    assert curve_speed_limit(line(20.0)) == 3.0


def test_a_gentle_arc_far_enough_does_not_slow_the_robot():
    assert curve_speed_limit(arc(radius=20.0)) == 3.0  # sqrt(1,0 x 20) = 4,5 m/s > 3,0


def test_a_tight_arc_limits_the_speed_to_sqrt_of_lateral_acceleration_over_curvature():
    # raio de 1 m e a_lat = 1 m/s² dão 1 m/s (a_brake = 0 isola o efeito da curva, sem distância de frenagem)
    assert curve_speed_limit(arc(radius=1.0), a_lat=1.0, a_brake=0.0) == pytest.approx(1.0, abs=0.05)
    assert curve_speed_limit(arc(radius=1.0), a_lat=2.0, a_brake=0.0) == pytest.approx(math.sqrt(2.0), abs=0.05)


def test_a_corner_ahead_brakes_gradually_so_the_robot_can_stop_in_time():
    near = curve_speed_limit(corner(before=1.0))
    mid = curve_speed_limit(corner(before=2.0))
    far = curve_speed_limit(corner(before=5.0))
    assert near < mid < far == 3.0
    # quina de 90° medida a cada 0,5 m: curvatura 2,83 1/m => 0,59 m/s; a 1 m dela: sqrt(0,59² + 2 x 1,5 x 1,0)
    assert near == pytest.approx(math.sqrt(0.594 ** 2 + 2 * 1.5 * 1.0), abs=0.1)


def test_a_corner_beyond_the_lookahead_is_ignored():
    assert curve_speed_limit(corner(before=15.0)) == 3.0


def test_the_limit_never_drops_below_the_minimum_speed():
    assert curve_speed_limit(corner(before=0.5, after=2.0), v_min=0.3) >= 0.3
    assert curve_speed_limit([(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1), (0, 0)]) >= 0.3


def test_the_limit_never_exceeds_the_maximum_speed_and_short_paths_are_safe():
    assert curve_speed_limit(line(20.0), v_max=2.0) == 2.0
    assert curve_speed_limit([]) == 3.0
    assert curve_speed_limit([(0.0, 0.0)]) == 3.0


def test_remaining_path_starts_at_the_point_nearest_to_the_robot():
    path = line(2.0, step=0.5)
    assert remaining_path(path, 1.05, 0.2) == [(1.0, 0.0), (1.5, 0.0), (2.0, 0.0)]
    assert remaining_path([], 0, 0) == []
```

`test/test_curve_launch.py`:

```python
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

NAV_LAUNCH = ROOT / "robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py"
SETUP = ROOT / "robot/ros2_ws/src/geraldo_dispatcher/setup.py"


def test_the_nav_launch_starts_the_curve_limiter_with_the_cruise_speed():
    src = NAV_LAUNCH.read_text(encoding="utf-8")
    ast.parse(src)
    assert 'package="geraldo_dispatcher"' in src and 'executable="curve_limiter"' in src
    assert '"v_max": 3.0' in src and '"a_lat": 1.0' in src and '"use_sim_time": True' in src


def test_the_curve_limiter_is_an_installed_executable():
    assert "curve_limiter = geraldo_dispatcher.curve_node:main" in SETUP.read_text(encoding="utf-8")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_curves.py test/test_curve_launch.py -q)`
Expected: FAIL (`ModuleNotFoundError: No module named 'geraldo_dispatcher.curves'` e a asserção do `nav.launch.py`).

- [ ] **Step 3: Implementar a função pura**

`geraldo_dispatcher/curves.py`:

```python
import math

V_MAX = 3.0       # m/s: velocidade de cruzeiro (a mesma do Nav2)
A_LAT = 1.0       # m/s²: aceleração lateral aceita nas curvas (configurável no nó)
A_BRAKE = 1.5     # m/s²: frenagem planejada até a curva, abaixo dos 2,5 m/s² do suavizador de velocidade do Nav2
V_MIN = 0.3       # m/s: o limite nunca zera o robô
LOOKAHEAD = 10.0  # m do caminho à frente que contam
STEP = 0.5        # m entre os pontos em que a curvatura é medida (o /plan tem ruído a cada 5 cm)


def resample(path_xy: list[tuple[float, float]], step: float = STEP) -> list[tuple[float, float]]:
    """Pontos do caminho espaçados por `step` metros de comprimento de arco; o primeiro ponto é mantido."""
    if not path_xy:
        return []
    out, carried = [path_xy[0]], 0.0
    for (x0, y0), (x1, y1) in zip(path_xy, path_xy[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        while length > 0 and carried + length >= step:
            t = (step - carried) / length
            x0, y0 = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            out.append((x0, y0))
            length -= step - carried
            carried = 0.0
        carried += length
    return out


def curvature(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Curvatura (1/m) do círculo que passa por a, b e c (Menger); 0 se os pontos estão alinhados ou repetidos."""
    ab, bc, ca = math.dist(a, b), math.dist(b, c), math.dist(c, a)
    if min(ab, bc, ca) < 1e-9:
        return 0.0
    area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))  # 2 x a área do triângulo
    return 2 * area2 / (ab * bc * ca)


def curve_speed_limit(path_xy: list[tuple[float, float]], v_max: float = V_MAX, a_lat: float = A_LAT,
                      a_brake: float = A_BRAKE, v_min: float = V_MIN, lookahead: float = LOOKAHEAD,
                      step: float = STEP) -> float:
    """Velocidade máxima (m/s) agora, dada a curvatura do caminho à frente (o primeiro ponto é a posição do robô).

    Em cada ponto a curva permite `sqrt(a_lat / curvatura)`; como o robô precisa de distância para frear,
    o limite agora é o menor `sqrt(v_ponto² + 2 * a_brake * distância até o ponto)` dentro de `lookahead`.
    O resultado fica entre `v_min` e `v_max`.
    """
    points = resample(path_xy, step)
    limit = v_max
    for i in range(1, len(points) - 1):
        distance = i * step
        if distance > lookahead:
            break
        k = curvature(points[i - 1], points[i], points[i + 1])
        if k <= 0:
            continue
        v_curve = max(v_min, min(v_max, math.sqrt(a_lat / k)))
        limit = min(limit, math.sqrt(v_curve ** 2 + 2 * a_brake * distance))
    return max(v_min, min(v_max, limit))


def remaining_path(path_xy: list[tuple[float, float]], x: float, y: float) -> list[tuple[float, float]]:
    """O caminho a partir do ponto mais próximo de (x, y): o plano é refeito a cada 1 s e o robô já andou desde então."""
    if not path_xy:
        return []
    nearest = min(range(len(path_xy)), key=lambda i: math.dist(path_xy[i], (x, y)))
    return path_xy[nearest:]
```

- [ ] **Step 4: Implementar o nó, o executável e o launch**

`geraldo_dispatcher/curve_node.py`:

```python
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.msg import SpeedLimit
from nav_msgs.msg import Path
from rclpy.node import Node

from .curves import A_BRAKE, A_LAT, V_MAX, curve_speed_limit, remaining_path


class CurveLimiter(Node):
    """Publica em /speed_limit a velocidade que a curvatura do /plan à frente permite (a conta está em curves.py)."""

    def __init__(self) -> None:
        super().__init__("curve_limiter")
        self._v_max = self.declare_parameter("v_max", V_MAX).value
        self._a_lat = self.declare_parameter("a_lat", A_LAT).value
        self._a_brake = self.declare_parameter("a_brake", A_BRAKE).value
        self._path: list[tuple[float, float]] = []
        self._pose: tuple[float, float] | None = None
        self._last: float | None = None
        self._pub = self.create_publisher(SpeedLimit, "/speed_limit", 10)
        self.create_subscription(Path, "/plan", self._on_plan, 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        self.create_timer(0.1, self._tick)

    def _on_plan(self, msg: Path) -> None:
        self._path = [(s.pose.position.x, s.pose.position.y) for s in msg.poses]

    def _on_pose(self, msg: PoseWithCovarianceStamped) -> None:
        self._pose = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def _tick(self) -> None:
        if self._pose is None:
            return
        ahead = remaining_path(self._path, *self._pose)
        limit = round(curve_speed_limit(ahead, v_max=self._v_max, a_lat=self._a_lat, a_brake=self._a_brake), 2)
        if limit != self._last:  # o Nav2 guarda o último limite recebido: só publica quando muda
            self._last = limit
            self._pub.publish(SpeedLimit(percentage=False, speed_limit=limit))


def main() -> None:
    rclpy.init()
    rclpy.spin(CurveLimiter())
    rclpy.shutdown()
```

`setup.py` (novo executável):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/setup.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/setup.py
@@ -17,4 +17,7 @@
     description="Dispatcher do G.E.R.A.L.D.O.",
     license="MIT",
-    entry_points={"console_scripts": ["dispatcher = geraldo_dispatcher.node:main"]},
+    entry_points={"console_scripts": [
+        "dispatcher = geraldo_dispatcher.node:main",
+        "curve_limiter = geraldo_dispatcher.curve_node:main",
+    ]},
 )
```

`geraldo_nav/launch/nav.launch.py` (o `geraldo_nav` não declara `exec_depend` do `geraldo_dispatcher` porque o dispatcher já depende dele para os waypoints; isso fecharia um ciclo):

```diff
--- a/robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py
+++ b/robot/ros2_ws/src/geraldo_nav/launch/nav.launch.py
@@ -5,4 +5,5 @@
 from launch.actions import IncludeLaunchDescription
 from launch.launch_description_sources import PythonLaunchDescriptionSource
+from launch_ros.actions import Node
 
 
@@ -20,3 +21,10 @@
             }.items(),
         ),
+        # Desacelera nas curvas pelo /speed_limit (pacote geraldo_dispatcher; sem exec_depend para não fechar um ciclo com o geraldo_nav)
+        Node(
+            package="geraldo_dispatcher",
+            executable="curve_limiter",
+            parameters=[{"use_sim_time": True, "v_max": 3.0, "a_lat": 1.0, "a_brake": 1.5}],
+            output="screen",
+        ),
     ])
```

- [ ] **Step 5: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q && python3 -c "import geraldo_dispatcher.curve_node") && (cd robot/ros2_ws && colcon build --symlink-install 2>&1 | tail -2) && source robot/ros2_ws/install/setup.bash && ros2 pkg executables geraldo_dispatcher`
Expected: testes PASS e a lista `geraldo_dispatcher curve_limiter` e `geraldo_dispatcher dispatcher`.

- [ ] **Step 6: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher robot/ros2_ws/src/geraldo_nav/launch
git commit -m "feat(robo): desaceleracao em curvas pelo /speed_limit a partir do /plan

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

(O comportamento do nó na simulação é conferido na Task 9; `ros2 topic echo /speed_limit` mostra um valor novo a cada mudança. Uma consulta `ros2 topic info -v /speed_limit` pode listar também o `route_server` do Nav2 como publicador; o robô só usa o `curve_limiter`.)

---

### Task 5: Detecção de obstáculos na telemetria

**Files:**
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/obstacles.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/telemetry.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_obstacles.py`, `robot/ros2_ws/src/geraldo_dispatcher/test/test_telemetry.py`

**Interfaces:**
- Consumes: `Pose(x, y, yaw)` de `geraldo_dispatcher/waypoints.py`; `build_telemetry(state, pose, battery, delivery_id, route, obstacles, now)` já aceita `obstacles: list[tuple[float, float, float]]` (x, y, raio) e devolve `[{"x", "y", "radius"}]`; `geraldo_nav/maps/hospital.yaml` + `hospital.pgm`.
- Produces em `geraldo_dispatcher/obstacles.py`:
  - `detect_obstacles(ranges: list[float], angle_min: float, angle_increment: float, pose: Pose, is_static: Callable[[float, float], bool], range_min: float = 0.12, range_max: float = 12.0, lidar_x: float = 0.275, cluster_gap: float = 0.35, max_obstacles: int = 20) -> list[tuple[float, float, float]]` — função pura: cada feixe com retorno vira um ponto no `map` pela pose do AMCL (o LiDAR está 0,275 m à frente do `base_link`); descarta o que `is_static(x, y)` reconhece como parede; agrupa por proximidade (ligação simples, 0,35 m); devolve até 20 círculos `(x, y, raio)` arredondados a 0,01 m, os mais próximos do robô primeiro (raio mínimo 0,10 m).
  - `StaticMap(width, height, resolution, origin, occupied: bytes)`, `StaticMap.from_yaml(yaml_path) -> StaticMap` (lê o `hospital.yaml` e o PGM) e `StaticMap.occupied_near(x, y, radius) -> bool` (fora do mapa conta como ocupado). Constante `STATIC_TOLERANCE = 0.25` m.
  - `TelemetryReporter(..., log=print, obstacle_source: Callable[[], list[tuple[float, float, float]]] = lambda: [])`: o parâmetro novo é o último; uma falha da fonte é registrada no `log` e a telemetria segue com `obstacles = []`.
  - `GeraldoStateNode(estop, static_map)` ganha `scan`, a assinatura de `/scan` e o método `obstacles()`.

- [ ] **Step 1: Escrever os testes que falham**

`test/test_obstacles.py`:

```python
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.obstacles import StaticMap, detect_obstacles  # noqa: E402
from geraldo_dispatcher.waypoints import Pose  # noqa: E402

HOSPITAL_MAP = ROOT / "robot/ros2_ws/src/geraldo_nav/maps/hospital.yaml"
NEVER = lambda x, y: False  # noqa: E731  (nenhum ponto é parede)
ANGLE_MIN, INCREMENT = -1.5, 3.0 / 359


def scan_with(hits: dict[int, float], beams: int = 360, far: float = math.inf) -> list[float]:
    ranges = [far] * beams
    for index, value in hits.items():
        ranges[index] = value
    return ranges


def beam_at(angle: float) -> int:
    return round((angle - ANGLE_MIN) / INCREMENT)


def detect(ranges, pose=Pose(0.0, 0.0, 0.0), is_static=NEVER, **kwargs):
    return detect_obstacles(ranges, ANGLE_MIN, INCREMENT, pose, is_static, **kwargs)


def test_an_empty_scan_has_no_obstacles():
    assert detect(scan_with({})) == []
    assert detect(scan_with({}, far=12.0)) == []  # retorno no alcance máximo = nada à vista


def test_one_hit_ahead_becomes_a_point_in_front_of_the_lidar():
    (x, y, radius), = detect(scan_with({beam_at(0.0): 2.0}))
    assert x == pytest.approx(0.275 + 2.0, abs=0.01) and y == pytest.approx(0.0, abs=0.02)
    assert radius == 0.10  # raio mínimo


def test_the_pose_moves_and_turns_the_points_into_the_map_frame():
    pose = Pose(10.0, 20.0, math.pi / 2)  # olhando para +y
    (x, y, _), = detect(scan_with({beam_at(0.0): 2.0}), pose=pose)
    assert x == pytest.approx(10.0, abs=0.02) and y == pytest.approx(20.0 + 0.275 + 2.0, abs=0.02)


def test_points_that_match_the_static_map_are_dropped():
    wall = lambda x, y: x > 5.0  # noqa: E731
    ranges = scan_with({beam_at(0.0): 6.0, beam_at(0.5): 1.0})
    obstacles = detect(ranges, is_static=wall)
    assert len(obstacles) == 1 and obstacles[0][0] < 5.0


def test_neighbouring_points_form_one_obstacle_whose_radius_covers_them():
    hits = {i: 3.0 for i in range(beam_at(-0.05), beam_at(0.05) + 1)}  # um objeto de uns 30 cm de largura a 3 m
    (x, y, radius), = detect(scan_with(hits))
    assert x == pytest.approx(3.275, abs=0.05) and y == pytest.approx(0.0, abs=0.05)
    assert 0.1 <= radius <= 0.3


def test_far_apart_objects_stay_separate_and_the_closest_comes_first():
    ranges = scan_with({beam_at(-0.8): 5.0, beam_at(0.0): 2.0, beam_at(0.8): 8.0})
    obstacles = detect(ranges)
    assert len(obstacles) == 3
    distances = [math.hypot(x, y) for x, y, _ in obstacles]
    assert distances == sorted(distances)


def test_at_most_20_obstacles_are_reported():
    ranges = scan_with({i: 3.0 for i in range(0, 360, 8)})  # 45 pontos a uns 20 cm um do outro
    assert len(detect(ranges, cluster_gap=0.05)) == 20       # com o gap menor que isso nenhum se junta
    assert len(detect(ranges, cluster_gap=0.05, max_obstacles=5)) == 5
    assert len(detect(ranges)) == 1                           # com o gap padrão (35 cm) viram um só


def test_readings_outside_the_sensor_range_are_ignored():
    assert detect(scan_with({10: 0.05, 11: math.nan, 12: 12.0, 13: math.inf})) == []


def test_results_are_rounded_to_centimetres():
    (x, y, radius), = detect(scan_with({beam_at(0.3): 2.123456}))
    assert (x, y, radius) == (round(x, 2), round(y, 2), round(radius, 2))


def test_static_map_loaded_from_the_hospital_files():
    static = StaticMap.from_yaml(HOSPITAL_MAP)
    assert (static.width, static.height, static.resolution) == (920, 600, 0.05)
    assert static.occupied_near(0.05, 15.0, 0.1)           # parede oeste (x = 0)
    assert not static.occupied_near(6.5, 26.5, 0.25)       # a base do robô está livre
    assert not static.occupied_near(23.0, 29.0, 0.25)      # corredor norte, onde a maca é colocada
    assert static.occupied_near(-1.0, 5.0, 0.1)            # fora do mapa não é obstáculo novo


def test_static_map_tolerance_catches_points_just_off_a_wall():
    static = StaticMap.from_yaml(HOSPITAL_MAP)
    assert static.occupied_near(0.25, 15.0, 0.25)
    assert not static.occupied_near(0.6, 15.0, 0.25)


def test_a_toy_map_flips_the_image_so_row_zero_is_the_bottom():
    # 3x2 células, 1 m cada: só a célula (col 2, linha de baixo) ocupada
    static = StaticMap(3, 2, 1.0, (0.0, 0.0), bytes([0, 0, 1, 0, 0, 0]))
    assert static.occupied_near(2.5, 0.5, 0.1) and not static.occupied_near(2.5, 1.5, 0.1)
```

Em `test/test_telemetry.py`, aplique o diff (o helper `reporter` aceita `**extra` e entram três testes):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/test/test_telemetry.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/test/test_telemetry.py
@@ -70,10 +70,10 @@
 
 
-def reporter(sink, pose=Pose(1, 2, 0.5), logs=None, levels=None):
+def reporter(sink, pose=Pose(1, 2, 0.5), logs=None, levels=None, **extra):
     return TelemetryReporter(
         sink, StateMachine(), BatteryModel(level=80.0), pose_source=lambda: pose,
         route_source=lambda: [(1, 2), (3, 4)], delivery_source=lambda: 7,
         on_battery=(levels if levels is not None else []).append, clock=lambda: NOW,
-        log=(logs if logs is not None else []).append,
+        log=(logs if logs is not None else []).append, **extra,
     )
 
@@ -97,2 +97,23 @@
     reporter(Sink(fails=True), logs=logs).tick(1.0)
     assert logs and "telemetria não enviada" in logs[0]
+
+
+def test_tick_sends_the_obstacles_the_source_reports():
+    sink = Sink()
+    reporter(sink, obstacle_source=lambda: [(23.0, 29.0, 1.0)]).tick(1.0)
+    assert sink.bodies[0]["obstacles"] == [{"x": 23.0, "y": 29.0, "radius": 1.0}]
+
+
+def test_without_an_obstacle_source_the_list_is_empty():
+    sink = Sink()
+    reporter(sink).tick(1.0)
+    assert sink.bodies[0]["obstacles"] == []
+
+
+def test_a_failing_obstacle_source_is_logged_and_the_rest_of_the_telemetry_still_goes():
+    def broken():
+        raise ValueError("scan inválido")
+
+    sink, logs = Sink(), []
+    reporter(sink, logs=logs, obstacle_source=broken).tick(1.0)
+    assert sink.bodies[0]["obstacles"] == [] and "obstáculos não calculados: scan inválido" in logs[0]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_obstacles.py test/test_telemetry.py -q)`
Expected: FAIL (`ModuleNotFoundError: No module named 'geraldo_dispatcher.obstacles'` e `unexpected keyword argument 'obstacle_source'`).

- [ ] **Step 3: Implementar**

`geraldo_dispatcher/obstacles.py`:

```python
import math
from collections.abc import Callable
from pathlib import Path

import yaml

from .waypoints import Pose

LIDAR_X = 0.275          # m: o lidar_link fica 27,5 cm à frente do base_link (geraldo.urdf.xacro)
STATIC_TOLERANCE = 0.25  # m: um ponto a menos disso de uma parede do mapa é a própria parede (erro do AMCL e do mapa)
CLUSTER_GAP = 0.35       # m: pontos a menos disso um do outro formam o mesmo obstáculo
MAX_OBSTACLES = 20       # contrato: Telemetry.obstacles
MIN_RADIUS = 0.10        # m


class StaticMap:
    """Mapa de ocupação do hospital (o hospital.yaml + hospital.pgm do Nav2), só para saber o que já é parede."""

    def __init__(self, width: int, height: int, resolution: float, origin: tuple[float, float], occupied: bytes) -> None:
        self.width, self.height, self.resolution, self.origin = width, height, resolution, origin
        self._occupied = occupied  # uma linha por vez, de baixo (y menor) para cima; 1 = ocupada

    @classmethod
    def from_yaml(cls, yaml_path) -> "StaticMap":
        yaml_path = Path(yaml_path)
        meta = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        raw = (yaml_path.parent / meta["image"]).read_bytes()
        magic, width, height, maxval, pixels = _parse_pgm(raw)
        threshold = float(meta["occupied_thresh"])
        negate = int(meta.get("negate", 0))
        rows = []
        for row in range(height - 1, -1, -1):  # o PGM começa pelo topo; o mapa, por baixo
            chunk = pixels[row * width:(row + 1) * width]
            rows.append(bytes(1 if _occupancy(p / maxval, negate) > threshold else 0 for p in chunk))
        return cls(width, height, float(meta["resolution"]), (float(meta["origin"][0]), float(meta["origin"][1])), b"".join(rows))

    def occupied_near(self, x: float, y: float, radius: float) -> bool:
        """True se há célula ocupada a até `radius` m de (x, y). Fora do mapa conta como ocupado (não é um obstáculo novo)."""
        col = math.floor((x - self.origin[0]) / self.resolution)
        row = math.floor((y - self.origin[1]) / self.resolution)
        if not (0 <= col < self.width and 0 <= row < self.height):
            return True
        reach = math.ceil(radius / self.resolution)
        for r in range(max(0, row - reach), min(self.height, row + reach + 1)):
            for c in range(max(0, col - reach), min(self.width, col + reach + 1)):
                if self._occupied[r * self.width + c] and math.hypot(c - col, r - row) * self.resolution <= radius:
                    return True
        return False


def _parse_pgm(raw: bytes) -> tuple[str, int, int, int, bytes]:
    """PGM binário (P5): devolve (magic, largura, altura, valor máximo, pixels)."""
    fields, pos = [], 0
    while len(fields) < 4:
        while raw[pos:pos + 1].isspace():
            pos += 1
        if raw[pos:pos + 1] == b"#":
            pos = raw.index(b"\n", pos)
            continue
        end = pos
        while not raw[end:end + 1].isspace():
            end += 1
        fields.append(raw[pos:end])
        pos = end
    pos += 1  # um único espaço separa o cabeçalho dos pixels
    if fields[0] != b"P5":
        raise ValueError("Mapa em formato PGM não suportado: use P5 (binário).")
    return "P5", int(fields[1]), int(fields[2]), int(fields[3]), raw[pos:]


def _occupancy(brightness: float, negate: int) -> float:
    """Probabilidade de ocupação de um pixel (convenção do map_server: pixel escuro = ocupado, a menos de `negate`)."""
    return brightness if negate else 1.0 - brightness


def detect_obstacles(ranges: list[float], angle_min: float, angle_increment: float, pose: Pose,
                     is_static: Callable[[float, float], bool], range_min: float = 0.12, range_max: float = 12.0,
                     lidar_x: float = LIDAR_X, cluster_gap: float = CLUSTER_GAP,
                     max_obstacles: int = MAX_OBSTACLES) -> list[tuple[float, float, float]]:
    """Obstáculos que o LiDAR vê e o mapa não tem, como círculos (x, y, raio) em metros no referencial `map`.

    Cada feixe com retorno vira um ponto no `map` (pela pose do AMCL); o que `is_static` reconhece como parede é
    descartado; o resto é agrupado por proximidade. Os `max_obstacles` grupos mais próximos do robô saem primeiro.
    """
    cos_yaw, sin_yaw = math.cos(pose.yaw), math.sin(pose.yaw)
    points = []
    for i, r in enumerate(ranges):
        if not (math.isfinite(r) and range_min <= r < range_max - 0.01):
            continue
        angle = angle_min + i * angle_increment
        bx, by = lidar_x + r * math.cos(angle), r * math.sin(angle)  # no base_link
        x, y = pose.x + bx * cos_yaw - by * sin_yaw, pose.y + bx * sin_yaw + by * cos_yaw
        if not is_static(x, y):
            points.append((x, y))
    clusters = _cluster(points, cluster_gap)
    circles = []
    for members in clusters:
        cx = sum(p[0] for p in members) / len(members)
        cy = sum(p[1] for p in members) / len(members)
        radius = max(MIN_RADIUS, max(math.dist(p, (cx, cy)) for p in members))
        circles.append((round(cx, 2), round(cy, 2), round(radius, 2)))
    circles.sort(key=lambda c: math.dist((c[0], c[1]), (pose.x, pose.y)))
    return circles[:max_obstacles]


def _cluster(points: list[tuple[float, float]], gap: float) -> list[list[tuple[float, float]]]:
    """Agrupa por proximidade (ligação simples): dois pontos a menos de `gap` ficam no mesmo grupo."""
    clusters: list[list[tuple[float, float]]] = []
    for point in points:
        near = [c for c in clusters if any(math.dist(point, q) <= gap for q in c)]
        merged = [point]
        for c in near:
            merged += c
            clusters.remove(c)
        clusters.append(merged)
    return clusters
```

`geraldo_dispatcher/telemetry.py`:

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/telemetry.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/telemetry.py
@@ -64,6 +64,8 @@
                  pose_source: Callable[[], Pose | None], route_source: Callable[[], list],
                  delivery_source: Callable[[], int | None], on_battery: Callable[[float], None],
-                 clock: Callable[[], datetime], log=print) -> None:
+                 clock: Callable[[], datetime], log=print,
+                 obstacle_source: Callable[[], list[tuple[float, float, float]]] = lambda: []) -> None:
         self.sink, self.machine, self.battery = sink, machine, battery
+        self.obstacle_source = obstacle_source
         self.pose_source, self.route_source, self.delivery_source = pose_source, route_source, delivery_source
         self.on_battery, self.clock, self.log = on_battery, clock, log
@@ -75,5 +77,10 @@
         if pose is None:
             return
-        body = build_telemetry(self.machine.state, pose, level, self.delivery_source(), self.route_source(), [], self.clock())
+        try:
+            obstacles = self.obstacle_source()
+        except Exception as err:  # sem obstáculos a telemetria ainda vale: o estado e a pose seguem
+            self.log(f"obstáculos não calculados: {err}")
+            obstacles = []
+        body = build_telemetry(self.machine.state, pose, level, self.delivery_source(), self.route_source(), obstacles, self.clock())
         try:
             self.sink.send_telemetry(body)
```

`geraldo_dispatcher/node.py` (assina `/scan`, calcula os obstáculos e liga a fonte ao `TelemetryReporter`; carrega o mapa estático do pacote `geraldo_nav`):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py
@@ -14,6 +14,6 @@
 from rclpy.executors import SingleThreadedExecutor
 from rclpy.node import Node
-from rclpy.qos import DurabilityPolicy, QoSProfile
-from sensor_msgs.msg import BatteryState
+from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
+from sensor_msgs.msg import BatteryState, LaserScan
 from std_msgs.msg import Bool, String
 
@@ -21,4 +21,5 @@
 from .dispatcher import Dispatcher
 from .emergency import EmergencyStop
+from .obstacles import STATIC_TOLERANCE, StaticMap, detect_obstacles
 from .ports import BackendError, NavigationTuner, Navigator
 from .profiles import NavProfile
@@ -54,11 +55,12 @@
 
 class GeraldoStateNode(Node):
-    """Publica /geraldo/state e /geraldo/battery e guarda a última pose (AMCL) e a rota (/plan) para a telemetria."""
+    """Publica /geraldo/state e /geraldo/battery e guarda a última pose (AMCL), a rota (/plan) e o /scan para a telemetria."""
 
-    def __init__(self, estop: EmergencyStop) -> None:
+    def __init__(self, estop: EmergencyStop, static_map: StaticMap) -> None:
         super().__init__("geraldo_state")
-        self._estop = estop
+        self._estop, self._map = estop, static_map
         self.pose: Pose | None = None
         self.route: list[tuple[float, float]] = []
+        self.scan: LaserScan | None = None
         latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
         self._state_pub = self.create_publisher(String, "/geraldo/state", latched)
@@ -67,4 +69,5 @@
         self.create_subscription(Path, "/plan", self._on_plan, 10)
         self.create_subscription(Bool, "/geraldo/estop", self._on_estop, 10)
+        self.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)
 
     def _on_estop(self, msg: Bool) -> None:
@@ -86,4 +89,16 @@
     def _on_plan(self, msg: Path) -> None:
         self.route = downsample([(s.pose.position.x, s.pose.position.y) for s in msg.poses], 50)
+
+    def _on_scan(self, msg: LaserScan) -> None:
+        self.scan = msg
+
+    def obstacles(self) -> list[tuple[float, float, float]]:
+        """Obstáculos do último /scan que o mapa estático não explica (círculos x, y, raio no referencial map)."""
+        scan, pose = self.scan, self.pose
+        if scan is None or pose is None:
+            return []
+        return detect_obstacles(list(scan.ranges), scan.angle_min, scan.angle_increment, pose,
+                                lambda x, y: self._map.occupied_near(x, y, STATIC_TOLERANCE),
+                                range_min=scan.range_min, range_max=scan.range_max)
 
 
@@ -137,5 +152,6 @@
     machine, estop = StateMachine(), EmergencyStop()
 
-    state_node = GeraldoStateNode(estop)
+    static_map = StaticMap.from_yaml(os.path.join(get_package_share_directory("geraldo_nav"), "maps", "hospital.yaml"))
+    state_node = GeraldoStateNode(estop, static_map)
     machine.subscribe(state_node.publish_state)
     state_node.publish_state(machine.state)
@@ -153,4 +169,5 @@
         route_source=lambda: state_node.route, delivery_source=lambda: dispatcher.delivery_id,
         on_battery=state_node.publish_battery, clock=lambda: datetime.now(timezone.utc),
+        obstacle_source=state_node.obstacles,
     )
     threading.Thread(target=_every_second, args=(reporter,), daemon=True).start()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q && python3 -c "import geraldo_dispatcher.node") && python3 -m pytest tools robot -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat(robo): obstaculos reais na telemetria a partir do /scan e do mapa estatico

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

(A conferência na simulação, com a maca, está na Task 9, passo de obstáculos.)

---

### Task 6: Estop do backend no dispatcher

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/emergency.py` (reescrito)
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/api.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`
- Modify: `robot/scripts/fake_backend.py`
- Modify: `robot/scripts/contract_examples.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_emergency.py`, `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py`

**Interfaces:**
- Consumes: contrato da Task 1 (`GET /robot/estop` → `{"active": bool}`, papel `robo`).
- Produces:
  - `BackendPort.estop_active(self) -> bool` (abstrato; `GET /robot/estop`). `BackendClient.estop_active()` implementa; `BackendError` se o backend falhar. Quem implementa `BackendPort` em testes precisa do método (feito aqui em `ScriptedBackend` e no `_Backend` de `contract_examples.py`).
  - `EmergencyStop` (em `emergency.py`) vira a junção das fontes: `active -> bool` (verdadeiro se qualquer fonte estiver ligada), `set_source(source: str, active: bool)`, `engage()` e `release()` (a fonte `TOPIC`, como antes). Constantes `TOPIC = "topic"` e `BACKEND = "backend"`.
  - `BackendEstopPoller(backend: BackendPort, estop: EmergencyStop, log=print)` com `poll()`: liga/desliga a fonte `BACKEND` conforme `backend.estop_active()`; qualquer exceção mantém o último valor e é registrada no `log` (`"emergência do backend não consultada (...); mantendo o último valor"`).
  - O `Dispatcher` não muda: ele já para enquanto `estop.active` for verdadeiro; só sai com as duas fontes desligadas.
  - `FakeBackend` (`robot/scripts/fake_backend.py`): atributo `estop: bool = False`; `GET /robot/estop` → `200 {"active": estop}`; `POST /robot/estop` com `{"active": bool}` → `204` e atualiza; `GET /telemetry` → `200` com o último corpo recebido em `POST /robot/telemetry` (ou `404` se não houve).
  - `node.py`: um cliente próprio (`estop_client`) consulta a cada 1 s em outra thread; uma primeira consulta acontece antes da primeira meta.

- [ ] **Step 1: Escrever os testes que falham**

`test/test_emergency.py` (aplique o diff):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/test/test_emergency.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/test/test_emergency.py
@@ -5,5 +5,5 @@
 sys.path.insert(0, str(ROOT))
 
-from geraldo_dispatcher.emergency import EmergencyStop  # noqa: E402
+from geraldo_dispatcher.emergency import BACKEND, TOPIC, EmergencyStop  # noqa: E402
 
 
@@ -15,2 +15,14 @@
     estop.release()
     assert estop.active is False
+
+
+def test_it_stays_engaged_until_every_source_is_off():
+    estop = EmergencyStop()
+    estop.engage()
+    estop.set_source(BACKEND, True)
+    estop.release()                       # o tópico solta, o painel ainda segura
+    assert estop.active is True
+    estop.set_source(BACKEND, False)
+    assert estop.active is False
+    estop.set_source(BACKEND, True)       # e o contrário
+    assert estop.active is True and TOPIC != BACKEND
```

`test/test_dispatcher.py` (importa o poller, o `ScriptedBackend` ganha `estop_active`, e entram seis testes: cliente, fake backend, poller, emergência do backend, junção em dois passos e telemetria do fake):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py
@@ -10,5 +10,5 @@
 from geraldo_dispatcher.api import BackendClient  # noqa: E402
 from geraldo_dispatcher.dispatcher import Dispatcher  # noqa: E402
-from geraldo_dispatcher.emergency import EmergencyStop  # noqa: E402
+from geraldo_dispatcher.emergency import BACKEND, TOPIC, BackendEstopPoller, EmergencyStop  # noqa: E402
 from geraldo_dispatcher.ports import BackendError, BackendPort, NavigationTuner, Navigator  # noqa: E402
 from geraldo_dispatcher.profiles import DEFAULT_PROFILE, PROFILES  # noqa: E402
@@ -52,4 +52,7 @@
     def delivery_status(self, delivery_id):
         return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
+
+    def estop_active(self):
+        return False
 
 
@@ -352,2 +355,90 @@
     assert result["result"] == "FALHOU" and "404" in result["reason"]
     assert [e["event"] for e in backend.events] == ["LOADED", "ARRIVED", "FAILED"]
+
+
+def test_the_client_reads_the_panel_emergency_from_the_backend(backend):
+    client = client_for(backend)
+    client.login()
+    assert client.estop_active() is False
+    backend.estop = True
+    assert client.estop_active() is True
+    assert backend.calls.count("/robot/estop") == 2
+
+
+def test_the_fake_backend_accepts_the_panel_emergency_through_post(backend):
+    client = client_for(backend)
+    client.login()
+    client._json("POST", "/robot/estop", {"active": True})
+    assert backend.estop is True and client.estop_active() is True
+
+
+def test_the_fake_backend_serves_the_last_telemetry_it_received(backend):
+    client = client_for(backend)
+    client.login()
+    with pytest.raises(BackendError, match="404"):
+        client._json("GET", "/telemetry")
+    client.send_telemetry({"robot_state": "IDLE", "obstacles": [{"x": 23.0, "y": 29.0, "radius": 1.0}]})
+    assert client._json("GET", "/telemetry")["obstacles"] == [{"x": 23.0, "y": 29.0, "radius": 1.0}]
+
+
+class PanelBackend(ScriptedBackend):  # o painel: estop_active devolve o que o teste mandou, ou falha
+    def __init__(self, answers) -> None:
+        super().__init__([])
+        self.answers = list(answers)
+
+    def estop_active(self):
+        answer = self.answers.pop(0)
+        if isinstance(answer, Exception):
+            raise answer
+        return answer
+
+
+def test_the_poller_follows_the_backend_and_keeps_the_last_value_when_it_fails():
+    estop, logs = EmergencyStop(), []
+    answers = [True, BackendError("Backend fora do ar"), ValueError("corpo estranho"), False]
+    poller = BackendEstopPoller(PanelBackend(answers), estop, log=logs.append)
+    poller.poll()
+    assert estop.active is True
+    poller.poll()
+    assert estop.active is True and "mantendo o último valor" in logs[0]
+    poller.poll()
+    assert estop.active is True and len(logs) == 2
+    poller.poll()
+    assert estop.active is False
+
+
+def test_an_emergency_from_the_backend_holds_the_robot_like_the_topic_does():
+    estop = EmergencyStop()
+    estop.set_source(BACKEND, True)
+
+    def panel_releases_on_the_first_wait(spent):
+        def sleep(seconds):
+            spent.append(seconds)
+            estop.set_source(BACKEND, False)
+        return sleep
+
+    result, history, sleeps = run(ScriptedBackend([TASK]), estop=estop, sleep=panel_releases_on_the_first_wait)
+    assert result["result"] == "ENTREGUE" and history[:2] == [State.PARADA_EMERGENCIA, State.IDLE]
+    assert sleeps[0] == 0.5
+
+
+def test_the_robot_leaves_the_emergency_only_when_both_sources_are_off():
+    estop = EmergencyStop()
+    estop.engage()
+    estop.set_source(BACKEND, True)
+    seen = []
+
+    def releasing_in_two_steps(spent):
+        def sleep(seconds):
+            spent.append(seconds)
+            if len(spent) == 1:
+                estop.set_source(BACKEND, False)       # o painel libera, mas o tópico ainda segura
+            elif len(spent) == 3:
+                estop.release()                       # só agora as duas fontes estão desligadas
+            seen.append(estop.active)
+        return sleep
+
+    result, history, sleeps = run(ScriptedBackend([]), estop=estop, sleep=releasing_in_two_steps)
+    assert result is None and sleeps == [0.5, 0.5, 0.5]
+    assert seen == [True, True, False]
+    assert history == [State.PARADA_EMERGENCIA, State.IDLE]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_emergency.py test/test_dispatcher.py -q)`
Expected: FAIL (`ImportError: cannot import name 'BACKEND' from 'geraldo_dispatcher.emergency'`).

- [ ] **Step 3: Implementar a junção e o poller**

`geraldo_dispatcher/emergency.py` (arquivo inteiro):

```python
import threading

from .ports import BackendPort

TOPIC, BACKEND = "topic", "backend"


class EmergencyStop:
    """Bandeira da parada de emergência, junção de fontes: o tópico /geraldo/estop e o backend (painel web).

    O robô está parado se QUALQUER fonte estiver ligada; só sai da parada com todas desligadas. O ROS e o relógio
    de consulta ligam e desligam as fontes (outras threads); o dispatcher só consulta `active`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: dict[str, bool] = {}

    @property
    def active(self) -> bool:
        with self._lock:
            return any(self._sources.values())

    def set_source(self, source: str, active: bool) -> None:
        with self._lock:
            self._sources[source] = active

    def engage(self) -> None:  # o tópico /geraldo/estop
        self.set_source(TOPIC, True)

    def release(self) -> None:
        self.set_source(TOPIC, False)


class BackendEstopPoller:
    """A cada `poll()` (1 s) pergunta ao backend se o painel acionou a emergência e atualiza a fonte `backend`.

    Se a consulta falha, vale o último valor conhecido: um backend que cai não libera nem aciona o robô sozinho.
    """

    def __init__(self, backend: BackendPort, estop: EmergencyStop, log=print) -> None:
        self.backend, self.estop, self.log = backend, estop, log

    def poll(self) -> None:
        try:
            active = self.backend.estop_active()
        except Exception as err:  # qualquer falha (rede, 401, corpo estranho) mantém o valor; a thread não pode morrer
            self.log(f"emergência do backend não consultada ({err}); mantendo o último valor")
            return
        self.estop.set_source(BACKEND, active)
```

`geraldo_dispatcher/ports.py`:

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py
@@ -26,4 +26,8 @@
         """Status atual da entrega (DeliveryStatus do contrato)."""
 
+    @abstractmethod
+    def estop_active(self) -> bool:
+        """True se o painel acionou a parada de emergência (GET /robot/estop)."""
+
 
 class TelemetryPort(ABC):  # porta: só o que a telemetria precisa
```

`geraldo_dispatcher/api.py`:

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/api.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/api.py
@@ -7,5 +7,5 @@
 
 class BackendClient(BackendPort, TelemetryPort):  # ADAPTER: traduz a API HTTP do backend para as portas do robô
-    """Cliente mínimo do backend (só biblioteca padrão): login, tarefa, eventos, status da entrega e telemetria."""
+    """Cliente mínimo do backend (só biblioteca padrão): login, tarefa, eventos, status da entrega, emergência do painel e telemetria."""
 
     def __init__(self, base_url: str, username: str, password: str, timeout: float = 10.0) -> None:
@@ -71,4 +71,7 @@
         return self._json("GET", f"/deliveries/{delivery_id}")["status"]
 
+    def estop_active(self) -> bool:
+        return bool(self._json("GET", "/robot/estop")["active"])
+
     def send_telemetry(self, body: dict) -> None:
         self._json("POST", "/robot/telemetry", body)
```

- [ ] **Step 4: API falsa, exemplos e node**

`robot/scripts/fake_backend.py`:

```diff
--- a/robot/scripts/fake_backend.py
+++ b/robot/scripts/fake_backend.py
@@ -1,5 +1,6 @@
 #!/usr/bin/env python3
 """API falsa do robô para desenvolver o dispatcher sem o backend. Segue docs/contracts/openapi.yaml
-(POST /auth/login, POST /robot/next-task, POST /robot/events, POST /robot/telemetry e GET /deliveries/{id}).
+(POST /auth/login, POST /robot/next-task, POST /robot/events, POST /robot/telemetry, GET e POST /robot/estop,
+GET /telemetry e GET /deliveries/{id}).
 
 Uso: python robot/scripts/fake_backend.py --port 8000     (usuário `robo`, senha `robo-local`)
@@ -33,4 +34,5 @@
         self.reject_events = False          # responde 409 a todo evento
         self.delivery_status_code = 200     # outro valor: a consulta da entrega responde esse código
+        self.estop = False                  # emergência do painel: GET /robot/estop devolve, POST /robot/estop muda
         self.verbose = verbose
         backend = self
@@ -60,4 +62,8 @@
                 if self._unauthorized():
                     return
+                if self.path == "/robot/estop":
+                    return self._send(200, {"active": backend.estop})
+                if self.path == "/telemetry":
+                    return self._send(200, backend.telemetry[-1]) if backend.telemetry else self._send(404, {"detail": "Sem telemetria ainda."})
                 if backend.delivery_status_code != 200:
                     return self._send(backend.delivery_status_code, {"detail": "Entrega não encontrada."})
@@ -89,4 +95,7 @@
                     backend.events.append(body)
                     return self._send(200, {"id": body["delivery_id"], "status": "EM_ROTA"})
+                if self.path == "/robot/estop":
+                    backend.estop = bool(json.loads(raw)["active"])
+                    return self._send(204)
                 if self.path == "/robot/telemetry":
                     backend.telemetry.append(json.loads(raw))
```

`robot/scripts/contract_examples.py` (o backend de mentira dos exemplos precisa da porta nova):

```diff
--- a/robot/scripts/contract_examples.py
+++ b/robot/scripts/contract_examples.py
@@ -65,4 +65,7 @@
         return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
 
+    def estop_active(self):
+        return False
+
 
 class _Navigator(Navigator):
```

`geraldo_dispatcher/node.py` (cliente próprio, primeira consulta antes da primeira meta e thread de 1 s; `_every_second` vira `_repeat(action, period)`):

```diff
--- a/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py
+++ b/robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py
@@ -20,5 +20,5 @@
 from .api import BackendClient
 from .dispatcher import Dispatcher
-from .emergency import EmergencyStop
+from .emergency import BackendEstopPoller, EmergencyStop
 from .obstacles import STATIC_TOLERANCE, StaticMap, detect_obstacles
 from .ports import BackendError, NavigationTuner, Navigator
@@ -118,8 +118,8 @@
 
 
-def _every_second(reporter: TelemetryReporter) -> None:
+def _repeat(action, period: float) -> None:
     while rclpy.ok():
-        time.sleep(1.0)
-        reporter.tick(1.0)
+        time.sleep(period)
+        action()
 
 
@@ -160,4 +160,10 @@
     threading.Thread(target=executor.spin, daemon=True).start()
 
+    estop_client = BackendClient(api_url, "robo", password)  # cliente próprio: a consulta da emergência roda em outra thread
+    _login_when_available(estop_client, "emergência")
+    poller = BackendEstopPoller(estop_client, estop)
+    poller.poll()  # uma parada já acionada no painel vale antes da primeira meta
+    threading.Thread(target=_repeat, args=(poller.poll, 1.0), daemon=True).start()
+
     dispatcher = Dispatcher(client, load_poses(waypoints_file), Nav2Navigator(nav, timeout=300, estop=estop),
                             machine=machine, estop=estop, tuner=Nav2Tuner(state_node))
@@ -171,5 +177,5 @@
         obstacle_source=state_node.obstacles,
     )
-    threading.Thread(target=_every_second, args=(reporter,), daemon=True).start()
+    threading.Thread(target=_repeat, args=(lambda: reporter.tick(1.0), 1.0), daemon=True).start()
     try:
         while rclpy.ok():
```

- [ ] **Step 5: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q && python3 -c "import geraldo_dispatcher.node") && python3 -m pytest tools robot -q`
Expected: PASS (os exemplos de `docs/contracts/examples/` não mudam: `git status --short docs/contracts/examples` vazio).

- [ ] **Step 6: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher robot/scripts/fake_backend.py robot/scripts/contract_examples.py
git commit -m "feat(robo): estop do painel pelo backend, junto com o topico /geraldo/estop

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Câmera RGB-D no URDF e na ponte

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro`
- Modify: `robot/ros2_ws/src/geraldo_description/config/bridge.yaml`
- Test: `robot/ros2_ws/src/geraldo_description/test/test_urdf.py`, `robot/ros2_ws/src/geraldo_description/test/test_launch_files.py`

**Interfaces:**
- Consumes: nada de tarefas anteriores.
- Produces: link `camera_link` e junta fixa `camera_joint` (pai `base_link`, origem `0.30 0 0.40`, olhando para +X); sensor Gazebo `rgbd_camera` de nome `camera`, tópico Gazebo `camera` (o Gazebo publica `/camera/image` e `/camera/depth_image`), 320 x 240, 10 Hz, 1,2 rad de campo de visão, alcance de 0,1 a 10 m. Ponte (GZ → ROS, `sensor_msgs/msg/Image`, `gz.msgs.Image`): `/camera/color/image_raw` ← `/camera/image` e `/camera/depth/image_raw` ← `/camera/depth_image`. **Sem leitura de marcador**: nenhum nó consome as imagens.

- [ ] **Step 1: Escrever os testes que falham**

`test/test_urdf.py` (a lista de links e juntas inclui a câmera, e entram dois testes):

```diff
--- a/robot/ros2_ws/src/geraldo_description/test/test_urdf.py
+++ b/robot/ros2_ws/src/geraldo_description/test/test_urdf.py
@@ -32,9 +32,9 @@
 def test_links_and_joints_exist(robot):
     assert {l.get("name") for l in robot.findall("link")} == {
-        "base_link", "wheel_left_link", "wheel_right_link", "caster_swivel_link", "caster_wheel_link", "lidar_link",
+        "base_link", "wheel_left_link", "wheel_right_link", "caster_swivel_link", "caster_wheel_link", "lidar_link", "camera_link",
         *(f"range_{n}_link" for n in RANGE),
     }
     assert set(joints(robot)) == {
-        "wheel_left_joint", "wheel_right_joint", "caster_swivel_joint", "caster_wheel_joint", "lidar_joint",
+        "wheel_left_joint", "wheel_right_joint", "caster_swivel_joint", "caster_wheel_joint", "lidar_joint", "camera_joint",
         *(f"range_{n}_joint" for n in RANGE),
     }
@@ -160,2 +160,17 @@
     assert float(sensor.find("lidar/range/max").text) == pytest.approx(2.0)
 
+
+def test_rgbd_camera_sits_on_the_front_of_the_trunk_looking_forward(robot):
+    joint = joints(robot)["camera_joint"]
+    assert joint.get("type") == "fixed" and joint.find("parent").get("link") == "base_link"
+    assert joint.find("child").get("link") == "camera_link"
+    assert xyz(joint) == pytest.approx([0.30, 0.0, 0.40])
+
+
+def test_rgbd_camera_publishes_color_and_depth_on_the_camera_topic(robot):
+    sensor = next(s for g in robot.findall("gazebo") if g.get("reference") == "camera_link" for s in g.findall("sensor"))
+    assert sensor.get("type") == "rgbd_camera"
+    assert sensor.find("topic").text == "camera"                # o Gazebo cria camera/image e camera/depth_image
+    assert sensor.find("gz_frame_id").text == "camera_link"
+    assert int(sensor.find("camera/image/width").text) == 320 and int(sensor.find("camera/image/height").text) == 240
+    assert float(sensor.find("camera/depth_camera/clip/far").text) == pytest.approx(10.0)
```

`test/test_launch_files.py` (a ponte tem os dois tópicos novos):

```diff
--- a/robot/ros2_ws/src/geraldo_description/test/test_launch_files.py
+++ b/robot/ros2_ws/src/geraldo_description/test/test_launch_files.py
@@ -12,9 +12,16 @@
     assert set(by_topic) == {"/clock", "/cmd_vel", "/odom", "/tf", "/scan",
                              "/range/front_c", "/range/front_l45", "/range/front_r45",
-                             "/range/rear_l135", "/range/rear_r135"}
-    for topic in set(by_topic) - {"/clock", "/cmd_vel", "/odom", "/tf"}:
+                             "/range/rear_l135", "/range/rear_r135",
+                             "/camera/color/image_raw", "/camera/depth/image_raw"}
+    for topic in set(by_topic) - {"/clock", "/cmd_vel", "/odom", "/tf", "/camera/color/image_raw", "/camera/depth/image_raw"}:
         assert by_topic[topic]["ros_type_name"] == "sensor_msgs/msg/LaserScan"
         assert by_topic[topic]["gz_type_name"] == "gz.msgs.LaserScan"
         assert by_topic[topic]["direction"] == "GZ_TO_ROS"
+    for topic in ("/camera/color/image_raw", "/camera/depth/image_raw"):  # câmera RGB-D: só imagens, do Gazebo para o ROS
+        assert by_topic[topic]["ros_type_name"] == "sensor_msgs/msg/Image"
+        assert by_topic[topic]["gz_type_name"] == "gz.msgs.Image"
+        assert by_topic[topic]["direction"] == "GZ_TO_ROS"
+    assert by_topic["/camera/color/image_raw"]["gz_topic_name"] == "/camera/image"
+    assert by_topic["/camera/depth/image_raw"]["gz_topic_name"] == "/camera/depth_image"
     assert by_topic["/cmd_vel"]["direction"] == "ROS_TO_GZ"
     assert by_topic["/cmd_vel"]["ros_type_name"] == "geometry_msgs/msg/Twist"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q)`
Expected: FAIL (`camera_joint`/`camera_link` ausentes e os tópicos `/camera/...` fora da ponte).

- [ ] **Step 3: Implementar**

`urdf/geraldo.urdf.xacro` (antes do bloco do `DiffDrive`):

```diff
--- a/robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro
+++ b/robot/ros2_ws/src/geraldo_description/urdf/geraldo.urdf.xacro
@@ -206,4 +206,44 @@
   <xacro:range_sensor name="rear_r135" x="-0.33" y="-0.26" yaw="-2.3562"/>
 
+  <!-- Câmera RGB-D na frente do baú, olhando para +X. Só publica imagens (cor e profundidade); nenhum nó lê marcador. -->
+  <link name="camera_link">
+    <inertial>
+      <mass value="0.05"/>
+      <inertia ixx="0.00001" ixy="0" ixz="0" iyy="0.00001" iyz="0" izz="0.00001"/>
+    </inertial>
+  </link>
+  <joint name="camera_joint" type="fixed">
+    <parent link="base_link"/>
+    <child link="camera_link"/>
+    <origin xyz="0.30 0 0.40"/>
+  </joint>
+  <gazebo reference="camera_link">
+    <sensor name="camera" type="rgbd_camera">
+      <pose>0 0 0 0 0 0</pose>
+      <topic>camera</topic>
+      <gz_frame_id>camera_link</gz_frame_id>
+      <update_rate>10</update_rate>
+      <always_on>true</always_on>
+      <visualize>false</visualize>
+      <camera>
+        <horizontal_fov>1.2</horizontal_fov>
+        <image>
+          <width>320</width>
+          <height>240</height>
+        </image>
+        <clip>
+          <near>0.1</near>
+          <far>10.0</far>
+        </clip>
+        <depth_camera>
+          <clip>
+            <near>0.1</near>
+            <far>10.0</far>
+          </clip>
+        </depth_camera>
+      </camera>
+    </sensor>
+  </gazebo>
+
   <gazebo>
     <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
```

`config/bridge.yaml` (acrescente ao final):

```diff
--- a/robot/ros2_ws/src/geraldo_description/config/bridge.yaml
+++ b/robot/ros2_ws/src/geraldo_description/config/bridge.yaml
@@ -58,2 +58,14 @@
   gz_type_name: gz.msgs.LaserScan
   direction: GZ_TO_ROS
+
+- ros_topic_name: /camera/color/image_raw
+  gz_topic_name: /camera/image
+  ros_type_name: sensor_msgs/msg/Image
+  gz_type_name: gz.msgs.Image
+  direction: GZ_TO_ROS
+
+- ros_topic_name: /camera/depth/image_raw
+  gz_topic_name: /camera/depth_image
+  ros_type_name: sensor_msgs/msg/Image
+  gz_type_name: gz.msgs.Image
+  direction: GZ_TO_ROS
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q) && python3 -m pytest tools robot -q`
Expected: PASS.

- [ ] **Step 5: Conferir as imagens na simulação**

Siga a "Receita de simulação" só até a simulação (sem o Nav2), depois:

Run: `export ROS_DOMAIN_ID=77 GZ_PARTITION=verif; source /opt/ros/jazzy/setup.bash; timeout 20 ros2 topic echo --once --field encoding /camera/color/image_raw; timeout 20 ros2 topic echo --once --field encoding /camera/depth/image_raw`
Expected: `rgb8` e `32FC1`. Se o Gazebo usar outros nomes de tópico, rode `gz topic -l | grep camera` e corrija o `gz_topic_name` na ponte **e** no teste (`test_bridge_has_the_contract_topics`). Abra o Gazebo com tela (`ros2 launch geraldo_description sim.launch.py`) e confira que a câmera não aparece dentro do baú nem solta no ar; se aparecer, ajuste `x` e `z` do `camera_joint` (e o teste que os trava). Derrube a simulação pelo PID (ver a receita).

- [ ] **Step 6: Commit**

```bash
git add robot/ros2_ws/src/geraldo_description
git commit -m "feat(robo): camera RGB-D no URDF e na ponte (/camera/color e /camera/depth)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Demo (`demo.sh` e roteiro), correção do `grep` e regras novas do `robot/AGENTS.md`

**Files:**
- Create: `robot/scripts/demo.sh` (executável)
- Create: `docs/demo-roteiro.md`
- Modify: `.vscode/tasks.json`
- Modify: `robot/AGENTS.md`
- Test: `robot/scripts/tests/test_demo_script.py`, `tools/tests/test_vscode_tasks.py`, `tools/tests/test_agents_docs.py`

**Interfaces:**
- Consumes: `robot/scripts/wait_for.sh`, `check_ros_env.sh`, `fake_backend.py` (Task 6: responde o estop), `spawn_stretcher.sh`, o executável `dispatcher` e o `nav.launch.py` com o `curve_limiter` (Task 4).
- Produces: `bash robot/scripts/demo.sh [--headless] [--fake-backend]` (sobe simulação, Nav2 e dispatcher; opção desconhecida sai com código 2 e a linha `uso:`); logs em `${TMPDIR:-/tmp}/geraldo-demo/`; `docs/demo-roteiro.md`; o `grep` das tarefas do VS Code passa a `grep -q '^active'` (a palavra `inactive` também contém `active`).

- [ ] **Step 1: Escrever os testes que falham**

`robot/scripts/tests/test_demo_script.py`:

```python
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEMO = ROOT / "robot/scripts/demo.sh"
ROTEIRO = ROOT / "docs/demo-roteiro.md"


def test_demo_script_is_executable_and_valid_bash():
    assert DEMO.is_file() and os.access(DEMO, os.X_OK)
    subprocess.run(["bash", "-n", str(DEMO)], check=True)


def test_demo_script_isolates_ros_and_never_kills_by_name():
    text = DEMO.read_text(encoding="utf-8")
    assert 'ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"' in text and 'GZ_PARTITION="${GZ_PARTITION:-verif}"' in text
    assert "pkill" not in text and "pgrep -f" not in text
    assert "kill -9 -- " in text  # o gz sim e o dispatcher só morrem com -9
    assert "grep -q '^active'" in text and "grep -q active" not in text
    for piece in ("sim.launch.py", "nav.launch.py", "geraldo_dispatcher dispatcher", "--fake-backend", "--headless"):
        assert piece in text, piece


def test_demo_script_rejects_unknown_options_before_starting_anything():
    result = subprocess.run(["bash", str(DEMO), "--nada"], capture_output=True, text=True)
    assert result.returncode == 2 and "uso:" in result.stderr


def test_the_demo_script_is_listed_by_the_robot_agents_file_and_the_roteiro_exists():
    assert "demo.sh" in (ROOT / "robot/AGENTS.md").read_text(encoding="utf-8")
    text = ROTEIRO.read_text(encoding="utf-8")
    for piece in ("demo.sh", "spawn_stretcher.sh", "3,0 m/s", "TODOS OS PONTOS OK", "Parada de emergência", "28/11"):
        assert piece in text, piece
```

`tools/tests/test_vscode_tasks.py` (acrescente ao final):

```diff
--- a/tools/tests/test_vscode_tasks.py
+++ b/tools/tests/test_vscode_tasks.py
@@ -42,2 +42,8 @@
     assert set(both["dependsOn"]) == {"GERALDO: simulação", "GERALDO: Nav2"}
     assert both["dependsOrder"] == "parallel"
+
+
+def test_the_sweep_waits_for_lifecycle_states_that_start_with_active():
+    command = BY_LABEL["GERALDO: varredura dos 10 pontos"]["command"]
+    assert command.count("grep -q '^active'") == 2   # "inactive" também contém "active"
+    assert "grep -q active" not in command
```

`tools/tests/test_agents_docs.py` (acrescente ao final):

```diff
--- a/tools/tests/test_agents_docs.py
+++ b/tools/tests/test_agents_docs.py
@@ -60,2 +60,12 @@
     text = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
     assert "construtor" in text and "if/elif" in text
+
+
+def test_robot_agents_describes_the_3_m_s_rule_and_the_week_3_pieces():
+    text = (ROOT / "robot/AGENTS.md").read_text(encoding="utf-8")
+    assert "**3,0 m/s sempre**" in text
+    for stale in ("Esse já é o teto", "crítica 1,0 m/s", "média 0,8 m/s", "rotina 0,5 m/s"):
+        assert stale not in text, stale
+    for piece in ("curve_limiter", "BackendEstopPoller", "detect_obstacles", "camera_link", "demo.sh", "measure_speed.py",
+                  "só o raio de inflação"):
+        assert piece in text, piece
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest robot/scripts/tests/test_demo_script.py tools/tests/test_vscode_tasks.py tools/tests/test_agents_docs.py -q`
Expected: FAIL (`demo.sh` não existe; o `grep -q active` ainda está no `tasks.json`; o `AGENTS.md` ainda tem "Esse já é o teto").

- [ ] **Step 3: Implementar o script, o roteiro e a correção do `tasks.json`**

`robot/scripts/demo.sh` (depois `chmod +x robot/scripts/demo.sh`):

```bash
#!/usr/bin/env bash
# Sobe a demo do G.E.R.A.L.D.O.: simulação (Gazebo), Nav2 com o limitador de curvas e o dispatcher.
# Uso: bash robot/scripts/demo.sh [--headless] [--fake-backend]
#   --headless       sem janela do Gazebo (só o servidor)
#   --fake-backend   sobe a API falsa em 127.0.0.1:8000 (usuário robo, senha robo-local) em vez de usar o backend real
# Sem --fake-backend, o backend real precisa estar de pé em GERALDO_API_URL (padrão http://127.0.0.1:8000) e a senha do
# robô em GERALDO_ROBOT_PASSWORD. Ctrl+C derruba tudo. Antes, na primeira vez: colcon build em robot/ros2_ws.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}" GZ_PARTITION="${GZ_PARTITION:-verif}"
HEADLESS=false
FAKE=false
for arg in "$@"; do
  case "$arg" in
    --headless) HEADLESS=true ;;
    --fake-backend) FAKE=true ;;
    *) echo "uso: bash robot/scripts/demo.sh [--headless] [--fake-backend]" >&2; exit 2 ;;
  esac
done

LOGS="${TMPDIR:-/tmp}/geraldo-demo"
mkdir -p "$LOGS"
PIDS=()

# Cada processo roda na própria sessão (setsid), então o PID é também o grupo: kill -9 -- -PID derruba o `ros2 launch`
# e os filhos dele (o gz sim só morre com -9). Nunca se mata por nome de processo: isso derruba o próprio shell.
start() {
  local name="$1"; shift
  setsid "$@" > "$LOGS/$name.log" 2>&1 &
  PIDS+=("$!")
  echo "iniciado: $name (PID $!, log em $LOGS/$name.log)"
}

cleanup() {
  trap - EXIT INT TERM
  echo "derrubando a demo..."
  for pid in "${PIDS[@]}"; do
    [ -n "$pid" ] && kill -9 -- "-$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

bash "$ROOT/robot/scripts/check_ros_env.sh"
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [ ! -f "$ROOT/robot/ros2_ws/install/setup.bash" ]; then
  echo "Falta compilar o workspace: (cd robot/ros2_ws && colcon build --symlink-install) e rode de novo." >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$ROOT/robot/ros2_ws/install/setup.bash"
set -u

if $FAKE; then
  export GERALDO_API_URL="http://127.0.0.1:8000" GERALDO_ROBOT_PASSWORD="robo-local"
  start api-falsa python3 "$ROOT/robot/scripts/fake_backend.py" --port 8000
else
  : "${GERALDO_ROBOT_PASSWORD:?Defina GERALDO_ROBOT_PASSWORD com a senha do usuário do robô (ou use --fake-backend).}"
  export GERALDO_API_URL="${GERALDO_API_URL:-http://127.0.0.1:8000}"
fi

start simulacao ros2 launch geraldo_description sim.launch.py "headless:=$HEADLESS"
bash "$ROOT/robot/scripts/wait_for.sh" "timeout 5 ros2 topic echo --once /scan" 120
start nav2 ros2 launch geraldo_nav nav.launch.py
bash "$ROOT/robot/scripts/wait_for.sh" "ros2 lifecycle get /amcl | grep -q '^active' && ros2 lifecycle get /bt_navigator | grep -q '^active'" 180
sleep 5
start dispatcher ros2 run geraldo_dispatcher dispatcher

cat <<EOF

DEMO NO AR (domínio ROS $ROS_DOMAIN_ID, API em $GERALDO_API_URL).
  maca no corredor:   bash robot/scripts/spawn_stretcher.sh on    (e "off" para tirar)
  logs:               $LOGS/*.log
  Ctrl+C derruba tudo. Roteiro completo em docs/demo-roteiro.md.
EOF

wait "${PIDS[${#PIDS[@]}-1]}" || true   # o último processo é o dispatcher: se ele cair, a demo termina
```

`docs/demo-roteiro.md`:

```markdown
# Roteiro da demo (ExpoTech, sábado 28/11/2026)

Quem executa: Samuel. Máquina: a dele (Pop!_OS 24.04, ROS 2 Jazzy e Gazebo Harmonic nativos). Duração: uns 8 minutos.

## Antes de sair de casa (quinta 26 e sexta 27)

1. `bash robot/scripts/check_ros_env.sh` deve terminar em `AMBIENTE OK`.
2. `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws && colcon build --symlink-install)`.
3. `python3 -m pytest tools robot -q` verde.
4. Varredura dos 10 pontos com a simulação e o Nav2 no ar (tarefa **GERALDO: varredura dos 10 pontos**): termina em `TODOS OS PONTOS OK`. O robô anda a 3,0 m/s sempre; se algum ponto falhar, não suba para a ExpoTech sem entender o motivo (ver `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md`).
5. Backend de pé (`cd backend && uvicorn app.main:app`) com o usuário `robo` e `GERALDO_ROBOT_PASSWORD` definida; sistema web aberto e com login feito.

## No palco

| # | O que fazer | O que a plateia vê |
|---|---|---|
| 1 | `bash robot/scripts/demo.sh` (na falta do backend real, `--fake-backend`). Espere `DEMO NO AR` | Gazebo com o hospital e o robô na base da farmácia |
| 2 | No sistema web, peça uma entrega de prioridade `critica` (banco de sangue para o centro cirúrgico) e aprove como farmacêutico | A entrega entra na fila e o estoque reserva os itens |
| 3 | O robô sai sozinho: `A_CAMINHO`, `CARREGANDO`, `A_CAMINHO` | Anda a 3,0 m/s no corredor e desacelera nas curvas e nas portas; o painel mostra rota e estado |
| 4 | Com o robô no corredor norte: `bash robot/scripts/spawn_stretcher.sh on` | A maca aparece no corredor, o robô a vê (obstáculo no painel) e replaneja pela cruz central |
| 5 | Botão **Parada de emergência** no painel | Estado `PARADA_EMERGENCIA` em até uns 2 s e o robô para. Libere no painel e ele retoma a mesma meta |
| 6 | `bash robot/scripts/spawn_stretcher.sh off` | Corredor livre |
| 7 | Chegada: `CHEGOU` e `AGUARDANDO_RETIRADA`. No painel, o solicitante confirma o recebimento | Tampa liberada (`UNLOCKED`), entrega `ENTREGUE` e o estoque do destino creditado |
| 8 | O robô volta à base (`VOLTANDO`, depois `IDLE`) | Baixa de estoque visível em Movimentações |

Se o robô parar sem motivo: veja `$TMPDIR/geraldo-demo/*.log` (padrão `/tmp/geraldo-demo`). Se a emergência não liberar, confira o tópico: `ros2 topic pub -r 5 -t 3 /geraldo/estop std_msgs/msg/Bool "{data: false}"` (o tópico e o painel precisam estar desligados).

## Depois

Ctrl+C no terminal do `demo.sh` derruba tudo (simulação, Nav2 e dispatcher). Se algo ficar vivo: `kill -9` no PID que o `demo.sh` imprimiu; nunca `pkill`.
```

`.vscode/tasks.json` (a tarefa "GERALDO: varredura dos 10 pontos"):

```diff
--- a/.vscode/tasks.json
+++ b/.vscode/tasks.json
@@ -38,5 +38,5 @@
       "label": "GERALDO: varredura dos 10 pontos",
       "type": "shell",
-      "command": "source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash && bash robot/scripts/wait_for.sh \"ros2 lifecycle get /amcl | grep -q active && ros2 lifecycle get /bt_navigator | grep -q active\" 180 && sleep 5 && python3 robot/scripts/nav_goal_sweep.py",
+      "command": "source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash && bash robot/scripts/wait_for.sh \"ros2 lifecycle get /amcl | grep -q '^active' && ros2 lifecycle get /bt_navigator | grep -q '^active'\" 180 && sleep 5 && python3 robot/scripts/nav_goal_sweep.py",
       "problemMatcher": [],
       "presentation": { "panel": "dedicated", "reveal": "always" }
```

- [ ] **Step 4: Reescrever as regras do `robot/AGENTS.md`**

Aplique em `robot/AGENTS.md` (a regra "1,0 m/s é o teto" vira "3,0 m/s sempre"; a linha dos perfis passa a só a inflação e a emergência ganha a segunda fonte; obstáculos, câmera e demo entram nas linhas que já existem):

```diff
--- a/robot/AGENTS.md
+++ b/robot/AGENTS.md
@@ -8,5 +8,5 @@
 |---|---|
 | `hospital/` | `hospital.yaml` (fonte única da planta e do mobiliário), `pieces.py` (catálogo das peças) e `gen_hospital.py`, que gera mundo, mapa, locais, waypoints, `maca.sdf` e `hospital_layout.json` (entrada do Blender). Testes em `hospital/tests/` |
-| `scripts/` | Ambiente (`check_ros_env.sh`), malhas 3D (`export_blender_mesh.py` e `export_hospital_mesh.py`), maca da demo (`spawn_stretcher.sh`), parâmetros do Nav2 (`make_nav2_params.py`), teste dos 10 pontos (`nav_goal_sweep.py`) e API falsa (`fake_backend.py`). Testes em `scripts/tests/` |
+| `scripts/` | Ambiente (`check_ros_env.sh`), malhas 3D (`export_blender_mesh.py` e `export_hospital_mesh.py`), maca da demo (`spawn_stretcher.sh`), parâmetros do Nav2 (`make_nav2_params.py`), teste dos 10 pontos (`nav_goal_sweep.py`), medição a 3 m/s (`measure_speed.py`), demo (`demo.sh`) e API falsa (`fake_backend.py`). Testes em `scripts/tests/` |
 | `ros2_ws/src/` | Pacotes ROS 2: `geraldo_description` (URDF, mundo, launch), `geraldo_nav` (mapa, waypoints, Nav2) e `geraldo_dispatcher` |
 
@@ -43,12 +43,12 @@
 - Rodas: `wheel_left_joint` e `wheel_right_joint` (eixo Y), separação de 0,45 m, raio de 0,10 m.
 - Rodízio articulado: `caster_swivel_joint` (eixo Z, pino em x = −0,25 e z = 0,09) e `caster_wheel_joint` (eixo Y), com a roda 1,5 cm atrás do pino (trail) e encostada no chão. Se ele vibrar na simulação, o plano B é voltar à esfera sem atrito (junta fixa).
-- Velocidade: o Nav2 cruza a 1,0 m/s (`CRUISE_SPEED` em `make_nav2_params.py`, no controlador e no suavizador) e o plugin de movimento do URDF aceita 1,0 m/s e 2,0 rad/s. Esse já é o teto: não suba mais sem rever as portas de 1 m e o raio de inflação.
+- Velocidade: **3,0 m/s sempre** (cerca de 10 km/h), para qualquer prioridade (pedido do líder, 13/11/2026). `CRUISE_SPEED` em `make_nav2_params.py` vale para o controlador e para o suavizador; o plugin de movimento do URDF aceita 3,0 m/s e 2,0 rad/s; o MPPI só chega lá com a janela de 18 m do costmap local e os ajustes `MPPI_TUNING` e `CRITIC_TUNING` do mesmo arquivo (não encolha a janela). O nó `curve_limiter` (`geraldo_dispatcher`, iniciado pelo `nav.launch.py`) lê o `/plan` e o `/amcl_pose` e baixa o limite pelo `/speed_limit` nas curvas: `v = min(3,0; √(a_lat / curvatura))`, com `a_lat` = 1,0 m/s² (parâmetro). Frenagem, curva de 90° e desvio da maca a 3 m/s estão medidos em `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md` (`robot/scripts/measure_speed.py`); se algo ali estiver marcado como não seguro, limitar a velocidade por trecho é decisão do líder.
 - Malhas: 5 arquivos em `geraldo_description/meshes/` (`geraldo_body`, `roda_esq`, `roda_dir`, `rodizio_garfo`, `rodizio_roda`), um por link do URDF, exportadas do `GeraldoV3.blend` em coordenadas do `base_link` (frente = +X). O visual de cada link desfaz o deslocamento da sua junta. Para exportar de novo: `blender -b modelos-3d/geraldoV3.blend --python robot/scripts/export_blender_mesh.py`. O `.blend` está em `modelos-3d/geraldoV3.blend`; `test_export_meshes.py` regenera as malhas dele e compara com as salvas, e `test_meshes.py` confere os `.obj` sem Blender.
 - Footprint do Nav2: retângulo 0,70 × 0,50 m (+10 cm de inflação).
 - Tópicos e estados: `docs/contracts/ros-interfaces.md`. Não crie tópico novo sem PR no contrato.
-- Dispatcher: `Dispatcher.run_once()` leva a entrega por `A_CAMINHO → CARREGANDO → A_CAMINHO → CHEGOU → AGUARDANDO_RETIRADA → VOLTANDO → IDLE` (`StateMachine` em `states.py`), avisa o backend com `LOADED`, `ARRIVED`, `UNLOCKED` ou `FAILED` e, em `AGUARDANDO_RETIRADA`, consulta `GET /deliveries/{id}` até virar `ENTREGUE`. `node.py` publica `/geraldo/state` e `/geraldo/battery` (bateria virtual) e manda `POST /robot/telemetry` a cada 1 s. Para rodar sem o backend: `python3 robot/scripts/fake_backend.py --port 8000` e `GERALDO_ROBOT_PASSWORD=robo-local ros2 run geraldo_dispatcher dispatcher`.
+- Dispatcher: `Dispatcher.run_once()` leva a entrega por `A_CAMINHO → CARREGANDO → A_CAMINHO → CHEGOU → AGUARDANDO_RETIRADA → VOLTANDO → IDLE` (`StateMachine` em `states.py`), avisa o backend com `LOADED`, `ARRIVED`, `UNLOCKED` ou `FAILED` e, em `AGUARDANDO_RETIRADA`, consulta `GET /deliveries/{id}` até virar `ENTREGUE`. `node.py` publica `/geraldo/state` e `/geraldo/battery` (bateria virtual) e manda `POST /robot/telemetry` a cada 1 s. Os `obstacles` da telemetria saem de `obstacles.py` (`detect_obstacles`: leva o `/scan` ao `map` pela pose do AMCL, descarta o que o `hospital.pgm` já tem, agrupa por proximidade e entrega até 20 círculos). Para rodar sem o backend: `python3 robot/scripts/fake_backend.py --port 8000` (responde também `GET`/`POST /robot/estop` e `GET /telemetry`) e `GERALDO_ROBOT_PASSWORD=robo-local ros2 run geraldo_dispatcher dispatcher`. Demo completa (simulação, Nav2 e dispatcher): `bash robot/scripts/demo.sh [--headless] [--fake-backend]`, com o roteiro em `docs/demo-roteiro.md`.
 - Protocolo com o backend, a web e o mock: `docs/contracts/robot-protocol.md`. Os exemplos de telemetria e de eventos (`docs/contracts/examples/`) são gerados por `python3 robot/scripts/contract_examples.py`; rode de novo ao mudar `build_telemetry`, os eventos ou os estados (o teste `test_contract_examples.py` falha se ficarem velhos).
-- Prioridades e emergência: cada entrega aplica o perfil da sua prioridade (`profiles.py`: crítica 1,0 m/s e inflação 0,55 m; média 0,8 m/s e 0,70 m; rotina 0,5 m/s e 0,70 m) pelo `/speed_limit` do Nav2 e pelo `inflation_layer.inflation_radius` do costmap local, e volta ao perfil médio no fim. `/geraldo/estop` (`std_msgs/Bool`) em `true` cancela a meta, para o robô e publica `PARADA_EMERGENCIA`; em `false` ele volta ao estado anterior e refaz a mesma meta. Teste na mão: `ros2 topic pub -r 5 -t 3 /geraldo/estop std_msgs/msg/Bool "{data: true}"`. **Aviso ao Erik:** "rotina só em baixo pico" não dá para impor no robô (a entrega já sai `EM_ROTA` do `next-task`); o `POST /robot/next-task` deve pular `rotina` fora da janela de baixo pico.
-- Sensores de alcance: `range_front_c`, `range_front_l45`, `range_front_r45`, `range_rear_l135` e `range_rear_r135` (macro `range_sensor` no URDF; 5 feixes de ±5° e até 2 m) saem em `/range/<nome>` (`LaserScan`, ponte em `config/bridge.yaml`). Nenhum a 180°. O Nav2 ainda não usa esses tópicos.
+- Prioridades e emergência: cada entrega aplica o perfil da sua prioridade (`profiles.py`, **só o raio de inflação**: crítica 0,55 m; média e rotina 0,70 m) pelo `inflation_layer.inflation_radius` do costmap local, e volta ao perfil médio no fim; a velocidade não depende da prioridade. A emergência junta duas fontes (`EmergencyStop` em `emergency.py`): o tópico `/geraldo/estop` (`std_msgs/Bool`) e o `GET /robot/estop` do backend, consultado a cada 1 s (`BackendEstopPoller`). Com qualquer uma ligada o robô cancela a meta, para e publica `PARADA_EMERGENCIA`; só sai da parada com as duas desligadas, então volta ao estado anterior e refaz a mesma meta; se a consulta ao backend falhar, vale o último valor. Teste na mão: `ros2 topic pub -r 5 -t 3 /geraldo/estop std_msgs/msg/Bool "{data: true}"`. **Aviso ao Erik:** "rotina só em baixo pico" não dá para impor no robô (a entrega já sai `EM_ROTA` do `next-task`); o `POST /robot/next-task` deve pular `rotina` fora da janela de baixo pico.
+- Sensores de alcance: `range_front_c`, `range_front_l45`, `range_front_r45`, `range_rear_l135` e `range_rear_r135` (macro `range_sensor` no URDF; 5 feixes de ±5° e até 2 m) saem em `/range/<nome>` (`LaserScan`, ponte em `config/bridge.yaml`). Nenhum a 180°. O Nav2 ainda não usa esses tópicos. A câmera RGB-D (`camera_link`, sensor `rgbd_camera` de 320 x 240 a 10 Hz e até 10 m) fica na frente do baú, com ponte em `/camera/color/image_raw` e `/camera/depth/image_raw`; é só imagem, sem leitura de marcador.
 - O mundo, o mapa e os waypoints são **gerados** por `robot/hospital/gen_hospital.py`; não edite os arquivos gerados à mão.
 
```

- [ ] **Step 5: Rodar e ver passar**

Run: `chmod +x robot/scripts/demo.sh && python3 -m pytest tools robot -q`
Expected: PASS. Confira também `bash robot/scripts/demo.sh --nada; echo $?` imprime `uso: ...` e `2`.

- [ ] **Step 6: Commit**

```bash
git add robot/scripts/demo.sh robot/scripts/tests/test_demo_script.py docs/demo-roteiro.md .vscode/tasks.json robot/AGENTS.md tools/tests/test_vscode_tasks.py tools/tests/test_agents_docs.py
git commit -m "docs(robo): demo.sh, roteiro da demo, grep ^active e regras de 3 m/s no AGENTS

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Medição a 3 m/s na simulação (frenagem, curva de 90°, maca) e obstáculos na telemetria

**Files:**
- Create: `robot/scripts/measure_speed.py`
- Create: `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md`
- Test: `robot/scripts/tests/test_measure_speed.py`

**Interfaces:**
- Consumes: simulação, Nav2 com o `curve_limiter` (Tasks 3 e 4), `spawn_stretcher.sh`, `worlds/maca.sdf` (caixa de 2,0 x 0,8 m em (23, 29) girada 90°, que ocupa x 22,6..23,4 e y 28..30 e bloqueia o corredor norte), `waypoints.yaml`, `fake_backend.py` (Task 6) e o dispatcher com a telemetria de obstáculos (Task 5).
- Produces: `python3 robot/scripts/measure_speed.py {freio|curva|maca|base} [--gap METROS]`, cada cenário imprime **uma** linha `RESULTADO ...`. Funções puras testadas: `stopping(samples, t_cmd) -> (distância m, tempo s) | None`, `peak_speed`, `peak_lateral_acceleration`, `speed_entering(samples, x_min, y_max)`, `distance_to_box`, `closest_approach`, `waypoint(name) -> (x, y, yaw em graus)`, `Sample`, `Box`, `MACA`. O relatório `2026-11-13-semana3-1-medicoes.md` com os números medidos.
- Regra desta tarefa (spec, seção 3): **se 3 m/s não for seguro, você reporta o número medido e propõe limite por trecho; não decide sozinho.** Não altere `CRUISE_SPEED` nem desligue o `curve_limiter` para "passar" na medição. A única exceção são os valores de `MPPI_TUNING`, `CRITIC_TUNING` e `LOCAL_COSTMAP_SIZE` (Task 3): se o robô não chegar a 2,85 m/s no corredor reto ou ficar preso (achado 1), ajuste esses valores em `make_nav2_params.py`, regenere o YAML (`python3 robot/scripts/make_nav2_params.py`), atualize os testes que os travam e registre os valores finais no relatório.

- [ ] **Step 1: Escrever os testes que falham**

`robot/scripts/tests/test_measure_speed.py`:

```python
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from robot.scripts.measure_speed import (  # noqa: E402
    MACA, Box, Sample, closest_approach, distance_to_box, peak_lateral_acceleration, peak_speed, speed_entering,
    stopping, waypoint,
)


def sample(t, ox=0.0, v=0.0, w=0.0, mx=None, my=None, scan_min=math.inf):
    return Sample(t, ox, 0.0, v, w, mx, my, scan_min)


def test_stopping_measures_distance_and_time_from_the_command_to_standstill():
    run = [sample(0.0, 0.0, 3.0), sample(1.0, 3.0, 3.0), sample(1.5, 4.5, 2.0), sample(2.0, 5.5, 0.9), sample(2.5, 5.9, 0.04)]
    assert stopping(run, t_cmd=1.0) == pytest.approx((2.9, 1.5))   # de x = 3,0 até x = 5,9, em 1,5 s


def test_stopping_is_none_when_the_robot_never_stops_or_there_is_nothing_after_the_command():
    assert stopping([sample(0.0, 0.0, 3.0), sample(1.0, 3.0, 3.0)], t_cmd=0.0) is None
    assert stopping([sample(0.0)], t_cmd=5.0) is None


def test_peaks_ignore_direction():
    run = [sample(0, v=-0.4, w=1.0), sample(1, v=2.0, w=0.5), sample(2, v=1.0, w=-1.9)]
    assert peak_speed(run) == 2.0
    assert peak_lateral_acceleration(run) == pytest.approx(1.9)
    assert peak_speed([]) == 0.0 and peak_lateral_acceleration([]) == 0.0


def test_speed_entering_a_door_uses_the_first_sample_past_the_line():
    run = [sample(0, v=3.0, mx=20.0, my=29.0), sample(1, v=2.0, mx=28.6, my=29.0), sample(2, v=1.2, mx=28.9, my=27.5),
           sample(3, v=0.5, mx=29.0, my=26.0)]
    assert speed_entering(run, x_min=28.0, y_max=28.0) == 1.2
    assert speed_entering(run[:2], x_min=28.0, y_max=28.0) is None
    assert speed_entering([sample(0, v=1.0)], x_min=0.0, y_max=100.0) is None   # sem AMCL ainda


def test_distance_to_box_is_zero_inside_and_euclidean_outside():
    box = Box(0.0, 0.0, 1.0, 2.0)
    assert distance_to_box(0.5, 1.0, box) == 0.0
    assert distance_to_box(3.0, 0.0, box) == pytest.approx(2.0)
    assert distance_to_box(4.0, 6.0, box) == pytest.approx(math.hypot(3.0, 4.0))


def test_closest_approach_takes_the_minimum_over_the_run():
    run = [sample(0, mx=15.0, my=29.0), sample(1, mx=21.0, my=29.0), sample(2, mx=18.0, my=29.0), sample(3)]
    assert closest_approach(run, MACA) == pytest.approx(22.6 - 21.0)
    assert closest_approach([sample(0)], MACA) == math.inf


def test_the_stretcher_box_matches_the_sdf_of_the_world():
    sdf = (ROOT / "robot/ros2_ws/src/geraldo_description/worlds/maca.sdf").read_text(encoding="utf-8")
    assert "<pose>23.000 29.000 0 0 0 1.5708</pose>" in sdf and "<size>2.000 0.800 0.900</size>" in sdf
    assert (MACA.cx, MACA.cy, MACA.hx, MACA.hy) == (23.0, 29.0, 0.4, 1.0)   # girada 90°: 0,8 m em x e 2,0 m em y


def test_the_goal_is_read_from_the_waypoints_file():
    assert waypoint("cc_entrega") == (29.0, 25.0, 90.0)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest robot/scripts/tests/test_measure_speed.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'robot.scripts.measure_speed'`).

- [ ] **Step 3: Implementar o script**

`robot/scripts/measure_speed.py` (o `rclpy` só é importado dentro das funções, então os testes rodam sem o ROS):

```python
#!/usr/bin/env python3
"""Mede o robô a 3 m/s na simulação: frenagem em corredor reto, curva de 90° e desvio da maca.

Uso (simulação e Nav2 rodando, ROS carregado, robô na base):
  python3 robot/scripts/measure_speed.py freio
  python3 robot/scripts/measure_speed.py curva
  python3 robot/scripts/measure_speed.py maca              # maca já no corredor antes de a meta sair
  python3 robot/scripts/measure_speed.py maca --gap 6      # maca aparece a 6 m do robô, em plena corrida
  python3 robot/scripts/measure_speed.py base              # leva o robô de volta à base entre uma medição e outra
Cada cenário termina com uma linha `RESULTADO ...`; copie-a para docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md.
Só mede e imprime: não muda nenhum parâmetro do robô.
"""
import argparse
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WAYPOINTS = ROOT / "robot/ros2_ws/src/geraldo_nav/config/waypoints.yaml"
SPAWN = ROOT / "robot/scripts/spawn_stretcher.sh"

CRUISE = 3.0          # m/s
STOPPED = 0.05        # m/s: abaixo disso o robô parou
FAST_ENOUGH = 2.85    # m/s: o freio só é medido a partir daqui
BRAKE_GOAL = (42.0, 29.0, 0.0)  # fim do corredor norte (y = 29): uns 35 m de reta depois da porta da farmácia
BRAKE_FROM_X = 25.0   # m: o comando de parada sai depois de o robô passar daqui já a velocidade de cruzeiro
TOUCH_DISTANCE = 0.35  # m: meio comprimento do robô; o centro a menos disso da borda da maca conta como encostar
DOOR_LINE = (28.0, 28.0)  # (x, y) da porta norte do centro cirúrgico: x >= 28 e y <= 28 = já virou para dentro dela
GOAL_TIMEOUT = 240.0  # s por meta


@dataclass(frozen=True)
class Sample:
    t: float           # s (relógio da simulação, vindo do /odom)
    ox: float          # m, posição no odom (para distâncias percorridas)
    oy: float
    v: float           # m/s, velocidade linear
    w: float           # rad/s, velocidade angular
    mx: float | None   # m, posição no mapa (último /amcl_pose); None até o AMCL publicar
    my: float | None
    scan_min: float    # m, menor leitura do /scan até agora nesta amostra (inf se ainda não há)


@dataclass(frozen=True)
class Box:
    cx: float
    cy: float
    hx: float  # meia largura em x
    hy: float  # meia largura em y


# A maca (worlds/maca.sdf): caixa de 2,0 x 0,8 m em (23, 29) girada 90°, então ocupa x 22,6..23,4 e y 28..30.
MACA = Box(23.0, 29.0, 0.4, 1.0)


def stopping(samples: list[Sample], t_cmd: float) -> tuple[float, float] | None:
    """(distância em m, tempo em s) do instante `t_cmd` até a primeira amostra com v < 0,05 m/s; None se nunca parou."""
    after = [s for s in samples if s.t >= t_cmd]
    if not after:
        return None
    start = after[0]
    for s in after[1:]:
        if s.v < STOPPED:
            return math.hypot(s.ox - start.ox, s.oy - start.oy), s.t - start.t
    return None


def peak_speed(samples: list[Sample]) -> float:
    return max((abs(s.v) for s in samples), default=0.0)


def peak_lateral_acceleration(samples: list[Sample]) -> float:
    """Maior |v x w| (m/s²): a aceleração lateral de um robô diferencial."""
    return max((abs(s.v * s.w) for s in samples), default=0.0)


def speed_entering(samples: list[Sample], x_min: float, y_max: float) -> float | None:
    """Velocidade na primeira amostra com x >= x_min e y <= y_max no mapa (a entrada de uma porta); None se não passou."""
    for s in samples:
        if s.mx is not None and s.my is not None and s.mx >= x_min and s.my <= y_max:
            return abs(s.v)
    return None


def distance_to_box(x: float, y: float, box: Box) -> float:
    """Distância de (x, y) à borda do retângulo (0 se estiver dentro)."""
    dx, dy = max(abs(x - box.cx) - box.hx, 0.0), max(abs(y - box.cy) - box.hy, 0.0)
    return math.hypot(dx, dy)


def closest_approach(samples: list[Sample], box: Box) -> float:
    """Menor distância do centro do robô à borda da caixa durante a corrida (inf se o AMCL não publicou)."""
    return min((distance_to_box(s.mx, s.my, box) for s in samples if s.mx is not None and s.my is not None),
               default=math.inf)


def waypoint(name: str) -> tuple[float, float, float]:
    """(x, y, yaw em graus) de um ponto do waypoints.yaml."""
    w = yaml.safe_load(WAYPOINTS.read_text(encoding="utf-8"))["waypoints"][name]
    return float(w["x"]), float(w["y"]), float(w["yaw"])


class Recorder:
    """Assina /odom, /amcl_pose e /scan no nó do navegador e guarda uma Sample a cada /odom."""

    def __init__(self, node) -> None:
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from nav_msgs.msg import Odometry
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import LaserScan

        self.samples: list[Sample] = []
        self._map: tuple[float, float] | None = None
        self._scan_min = math.inf
        node.create_subscription(Odometry, "/odom", self._on_odom, 50)
        node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_pose, 10)
        node.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)

    def _on_pose(self, msg) -> None:
        self._map = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def _on_scan(self, msg) -> None:
        valid = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
        if valid:
            self._scan_min = min(self._scan_min, min(valid))

    def _on_odom(self, msg) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        mx, my = self._map if self._map else (None, None)
        self.samples.append(Sample(t, msg.pose.pose.position.x, msg.pose.pose.position.y, msg.twist.twist.linear.x,
                                   msg.twist.twist.angular.z, mx, my, self._scan_min))

    @property
    def latest(self) -> Sample | None:
        return self.samples[-1] if self.samples else None


def goal_pose(nav, x: float, y: float, yaw_deg: float):
    from geometry_msgs.msg import PoseStamped

    goal = PoseStamped()
    goal.header.frame_id = "map"
    goal.header.stamp = nav.get_clock().now().to_msg()
    goal.pose.position.x, goal.pose.position.y = float(x), float(y)
    yaw = math.radians(yaw_deg)
    goal.pose.orientation.z, goal.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    return goal


def run_goal(nav, recorder: Recorder, goal, on_tick=lambda sample: None) -> bool:
    """Manda a meta e espera terminar (chamando `on_tick` a cada passo). True se o Nav2 chegou."""
    from nav2_simple_commander.robot_navigator import TaskResult

    nav.goToPose(goal)
    start = time.monotonic()
    while not nav.isTaskComplete():  # isTaskComplete gira o nó por 0,1 s, então o Recorder recebe as mensagens
        if recorder.latest is not None:
            on_tick(recorder.latest)
        if time.monotonic() - start > GOAL_TIMEOUT:
            nav.cancelTask()
            break
    return nav.getResult() == TaskResult.SUCCEEDED


def freio(nav, recorder: Recorder) -> str:
    import rclpy

    nav.goToPose(goal_pose(nav, *BRAKE_GOAL))
    start, t_cmd = time.monotonic(), None
    while t_cmd is None and time.monotonic() - start < GOAL_TIMEOUT and not nav.isTaskComplete():
        s = recorder.latest
        if s is not None and s.mx is not None and s.mx >= BRAKE_FROM_X and s.v >= FAST_ENOUGH:
            t_cmd = s.t
            v_cmd = s.v
            nav.cancelTask()  # é o que o dispatcher faz na parada de emergência
    if t_cmd is None:
        status = nav.getResult()
        nav.cancelTask()
        return (f"RESULTADO freio nao_atingiu_{CRUISE:.1f}_m_s pico={peak_speed(recorder.samples):.2f} m/s "
                f"fim_da_meta={status.name if hasattr(status, 'name') else status}")
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline and not (recorder.latest and recorder.latest.t > t_cmd and recorder.latest.v < STOPPED):
        rclpy.spin_once(nav, timeout_sec=0.05)
    result = stopping(recorder.samples, t_cmd)
    if result is None:
        return f"RESULTADO freio v_no_comando={v_cmd:.2f} m/s nao_parou_em_20_s"
    return f"RESULTADO freio v_no_comando={v_cmd:.2f} m/s distancia_ate_parar={result[0]:.2f} m tempo_ate_parar={result[1]:.2f} s"


def curva(nav, recorder: Recorder) -> str:
    x, y, yaw = waypoint("cc_entrega")  # sai da farmácia (90° para leste), corre o corredor e vira 90° para a porta do CC
    reached = run_goal(nav, recorder, goal_pose(nav, x, y, yaw))
    samples = recorder.samples
    door = speed_entering(samples, *DOOR_LINE)
    door_text = f"{door:.2f} m/s" if door is not None else "nao_passou"
    return (f"RESULTADO curva chegou={reached} v_max={peak_speed(samples):.2f} m/s "
            f"aceleracao_lateral_max={peak_lateral_acceleration(samples):.2f} m/s2 velocidade_na_porta={door_text} "
            f"menor_leitura_do_lidar={min((s.scan_min for s in samples), default=math.inf):.2f} m")


def base(nav, recorder: Recorder) -> str:
    x, y, yaw = waypoint("base_robo")
    reached = run_goal(nav, recorder, goal_pose(nav, x, y, yaw))
    return f"RESULTADO base chegou={reached}"


def set_stretcher(on: bool) -> None:
    subprocess.run(["bash", str(SPAWN), "on" if on else "off"], check=True, capture_output=True, text=True)


def maca(nav, recorder: Recorder, gap: float | None) -> str:
    x, y, yaw = waypoint("cc_entrega")
    spawned = gap is None
    if spawned:
        set_stretcher(True)
    try:
        def tick(sample: Sample) -> None:
            nonlocal spawned
            if not spawned and sample.mx is not None and sample.mx >= MACA.cx - MACA.hx - gap:
                set_stretcher(True)
                spawned = True

        reached = run_goal(nav, recorder, goal_pose(nav, x, y, yaw), tick)
    finally:
        set_stretcher(False)
    samples = recorder.samples
    closest = closest_approach(samples, MACA)
    how = "ja_no_corredor" if gap is None else f"surgiu_a_{gap:g}_m"
    return (f"RESULTADO maca {how} chegou={reached} v_max={peak_speed(samples):.2f} m/s "
            f"menor_distancia_a_borda_da_maca={closest:.2f} m encostou={closest <= TOUCH_DISTANCE}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cenario", choices=["freio", "curva", "maca", "base"])
    ap.add_argument("--gap", type=float, default=None, help="só em `maca`: metros entre o robô e a maca quando ela surge")
    args = ap.parse_args()

    import rclpy
    from nav2_simple_commander.robot_navigator import BasicNavigator

    rclpy.init()
    nav = BasicNavigator()
    nav.initial_pose_received = True  # o AMCL já nasce na base (nav2_params.yaml)
    nav.waitUntilNav2Active()
    recorder = Recorder(nav)
    try:
        if args.cenario == "freio":
            print(freio(nav, recorder))
        elif args.cenario == "curva":
            print(curva(nav, recorder))
        elif args.cenario == "base":
            print(base(nav, recorder))
        else:
            print(maca(nav, recorder, args.gap))
    finally:
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar, e commitar o script**

Run: `python3 -m pytest tools robot -q`
Expected: PASS.

```bash
chmod +x robot/scripts/measure_speed.py
git add robot/scripts/measure_speed.py robot/scripts/tests/test_measure_speed.py
git commit -m "feat(robo): script de medicao a 3 m/s (frenagem, curva e maca)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Subir a simulação e o Nav2**

Siga a "Receita de simulação" (simulação headless + Nav2, esperando `^active`). Confirme que o `curve_limiter` está vivo: `export ROS_DOMAIN_ID=77; source /opt/ros/jazzy/setup.bash; ros2 node list | grep curve_limiter` imprime `/curve_limiter`. O robô precisa estar na base (ele nasce lá).

- [ ] **Step 6: Medir os três cenários**

Rode cada comando abaixo com o ROS carregado e o `install/setup.bash` do workspace, `ROS_DOMAIN_ID=77` e `GZ_PARTITION=verif`; guarde **a linha `RESULTADO`** de cada um. Entre uma medição e outra, leve o robô de volta à base com `python3 robot/scripts/measure_speed.py base` (espere `RESULTADO base chegou=True`):

```bash
python3 robot/scripts/measure_speed.py freio        # frenagem em corredor reto, comando de parada a 2,85 m/s ou mais
python3 robot/scripts/measure_speed.py base
python3 robot/scripts/measure_speed.py curva        # farmácia -> corredor -> curva de 90° na porta do centro cirúrgico
python3 robot/scripts/measure_speed.py base
python3 robot/scripts/measure_speed.py maca         # maca já no corredor, o robô replaneja
python3 robot/scripts/measure_speed.py base
python3 robot/scripts/measure_speed.py maca --gap 8 # maca surge a 8 m do robô, em plena corrida
python3 robot/scripts/measure_speed.py base
python3 robot/scripts/measure_speed.py maca --gap 6
python3 robot/scripts/measure_speed.py base
python3 robot/scripts/measure_speed.py maca --gap 4
python3 robot/scripts/measure_speed.py base
```

Repita `freio` três vezes (com `base` entre elas) e anote os três números. Se o `freio` disser `nao_atingiu_3.0_m_s`, o robô não chegou a 2,85 m/s: aplique a exceção acima (ajuste de `MPPI_TUNING`/`CRITIC_TUNING`/`LOCAL_COSTMAP_SIZE`), derrube o Nav2 pelo PID, suba de novo e repita. Se o robô ficar preso na porta da farmácia ou a meta `FALHOU`, trate igual e registre. Se `spawn_stretcher.sh` falhar por já haver uma maca, rode `bash robot/scripts/spawn_stretcher.sh off` e repita.

Classifique cada cenário (isto é só rótulo; não muda nada no robô):
- **freio**: não seguro se `distancia_ate_parar` > 2,0 m (alcance dos sensores `/range/*`) ou se `nao_parou_em_20_s`.
- **curva**: não segura se `chegou=False` ou `menor_leitura_do_lidar` < 0,30 m.
- **maca**: não segura se `encostou=True` ou `chegou=False`.

- [ ] **Step 7: Conferir os obstáculos na telemetria (com a maca)**

Com a simulação e o Nav2 no ar e o robô na base, suba a API falsa e o dispatcher (cada um com `setsid`, gravando o PID em `${TMPDIR:-/tmp}/geraldo-api.pid` e `${TMPDIR:-/tmp}/geraldo-dispatcher.pid`, como na receita):

```bash
setsid python3 robot/scripts/fake_backend.py --port 8000 > "${TMPDIR:-/tmp}/geraldo-api.log" 2>&1 &
echo $! > "${TMPDIR:-/tmp}/geraldo-api.pid"
GERALDO_ROBOT_PASSWORD=robo-local GERALDO_API_URL=http://127.0.0.1:8000 setsid ros2 run geraldo_dispatcher dispatcher > "${TMPDIR:-/tmp}/geraldo-dispatcher.log" 2>&1 &
echo $! > "${TMPDIR:-/tmp}/geraldo-dispatcher.pid"
```

O `fake_backend.py` entrega duas tarefas (a 2ª, `banco_sangue_retirada` → `cc_entrega`, passa pelo corredor norte entre x = 17 e x = 29). Rode o laço abaixo: ele consulta a telemetria a cada 1 s, põe a maca quando o robô está no corredor norte na entrega 2 e a tira ao fim:

```bash
python3 - <<'PY' | tee "${TMPDIR:-/tmp}/geraldo-obstaculos.txt"
import json, subprocess, time, urllib.request

def telemetry():
    req = urllib.request.Request("http://127.0.0.1:8000/telemetry", headers={"Authorization": "Bearer fake-token-1"})
    return json.load(urllib.request.urlopen(req, timeout=3))

spawned = False
for _ in range(300):
    try:
        t = telemetry()
    except Exception:
        time.sleep(1)
        continue
    x, y = t["pose"]["x"], t["pose"]["y"]
    if not spawned and t["delivery_id"] == 2 and t["robot_state"] == "A_CAMINHO" and y > 28.5 and x > 14:
        subprocess.run(["bash", "robot/scripts/spawn_stretcher.sh", "on"], check=True)
        spawned = True
        print("MACA COLOCADA", flush=True)
    print(round(x, 1), round(y, 1), t["robot_state"], t["obstacles"], flush=True)
    if spawned and t["delivery_id"] is None:
        break
    time.sleep(1)
subprocess.run(["bash", "robot/scripts/spawn_stretcher.sh", "off"])
PY
```

Leia a saída: as linhas **antes** de `MACA COLOCADA` mostram os obstáculos sem maca (esperado `[]`; anote quantas linhas vieram com itens e em quais coordenadas, são falsos positivos). As linhas **depois** devem trazer, assim que a maca entra no alcance do LiDAR, **um item perto de (23, 29) com raio entre 0,5 e 1,2**. Se a maca nunca aparecer, anote a pose do robô nesse momento. Não ajuste `STATIC_TOLERANCE` nem `CLUSTER_GAP` por conta própria: registre e avise o coordenador (os valores estão descritos no `robot-protocol.md`).

Derrube o dispatcher, a API falsa, o Nav2 e a simulação pelos PIDs (`kill -9 -- -PID`).

- [ ] **Step 8: Escrever o relatório**

Crie `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md` com exatamente esta estrutura, preenchendo **cada valor com o que o script imprimiu** (nada de estimativa):

```markdown
# Medições a 3 m/s na simulação (semana 3, plano 1)

Data: <data da medição> · Branch: `feat/semana3-robo` · Commit: <git rev-parse --short HEAD> · Script: `robot/scripts/measure_speed.py` · Simulação: hospital 3D, `headless:=true`, `ROS_DOMAIN_ID=77`, `GZ_PARTITION=verif`.

Configuração do Nav2 usada: `CRUISE_SPEED` 3,0 m/s; janela do costmap local <LOCAL_COSTMAP_SIZE> m; `MPPI_TUNING` <valores finais>; `CRITIC_TUNING` <valores finais>; suavizador de velocidade com aceleração e desaceleração de 2,5 m/s²; `curve_limiter` com `a_lat` 1,0 m/s² e `a_brake` 1,5 m/s². Se os valores do MPPI foram mudados em relação à Task 3, diga o que mudou e por quê.

## Resultados

| Cenário | Linha `RESULTADO` impressa pelo script | Segurança (critério da Task 9) |
|---|---|---|
| freio (1ª) | `<linha>` | seguro / NÃO SEGURO |
| freio (2ª) | `<linha>` | |
| freio (3ª) | `<linha>` | |
| curva de 90° | `<linha>` | |
| maca já no corredor | `<linha>` | |
| maca surge a 8 m | `<linha>` | |
| maca surge a 6 m | `<linha>` | |
| maca surge a 4 m | `<linha>` | |

## Obstáculos na telemetria

- Sem maca: `<lista impressa>` (quantos itens, onde, se são falsos positivos).
- Com maca: `<lista impressa>` (esperado: um círculo perto de (23, 29)).

## Leitura

Um parágrafo por cenário dizendo o que o número significa (por exemplo, quantos metros o robô leva para parar a 3 m/s comparado com o alcance de 2 m dos sensores `/range/*` e com a largura de 1 m das portas).

## Proposta (só se algum cenário estiver NÃO SEGURO)

Limite por trecho sugerido (por exemplo, velocidade máxima nas portas de 1 m, nos cruzamentos e perto da maca), com a justificativa em números. **É proposta para o líder decidir: nada disto foi aplicado.** Se tudo estiver seguro, escreva "Nenhum cenário reprovou; 3,0 m/s mantido."
```

- [ ] **Step 9: Commit do relatório**

```bash
git add docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md robot/scripts/make_nav2_params.py robot/scripts/tests robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml
git commit -m "docs(robo): medicoes a 3 m/s na simulacao (frenagem, curva e maca)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

(Se você não alterou os valores do MPPI, `git add` só do relatório basta; o `git commit` falha sem nada novo apenas se o relatório faltar.)

---

### Task 10: Varredura dos 10 pontos no hospital 3D a 3 m/s

**Files:**
- Modify: `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md` (nova seção "Varredura dos 10 pontos")

**Interfaces:**
- Consumes: `robot/scripts/nav_goal_sweep.py` (termina em `TODOS OS PONTOS OK` com código 0, ou em `FALHARAM: [...]`), a simulação e o Nav2 com tudo da semana 3 (curvas, câmera, janela de 18 m), e o `grep -q '^active'` da Task 8.
- Produces: o texto de saída da varredura registrado no relatório da Task 9 e, se passar, o marco de pronto do robô desta semana (spec, seção 7).

- [ ] **Step 1: Subir a simulação e o Nav2 e esperar o lifecycle**

Siga a "Receita de simulação" inteira (o `wait_for.sh` já espera `^active` no `/amcl` e no `/bt_navigator`). Depois dê mais 5 s: `sleep 5`.

- [ ] **Step 2: Rodar a varredura**

Run: `export ROS_DOMAIN_ID=77 GZ_PARTITION=verif; source /opt/ros/jazzy/setup.bash; source robot/ros2_ws/install/setup.bash; python3 robot/scripts/nav_goal_sweep.py 2>&1 | tee "${TMPDIR:-/tmp}/geraldo-sweep.txt"`
Expected: dez linhas `ok  <ponto>  <segundos>s` e a última linha `TODOS OS PONTOS OK` (com 3 m/s tende a levar bem menos que os ~10 min de antes).

- [ ] **Step 3: Se algum ponto falhar**

1. Rode a varredura uma segunda vez (o AMCL pode ter se perdido no meio). Se passar na segunda, registre as duas saídas e que a primeira falhou, e em qual ponto.
2. Se o mesmo ponto falhar duas vezes: **não** afrouxe tolerâncias, não aumente timeouts e não reduza `CRUISE_SPEED`. Pare, registre a saída (`FALHARAM: [...]`, o ponto e o tempo) e a pose onde o robô ficou (`ros2 topic echo --once --field pose.pose.position /amcl_pose`) e proponha, na seção "Proposta" do relatório, o limite por trecho que resolveria (por exemplo, velocidade máxima nas portas de 1 m). O coordenador decide. Se o problema for o robô preso por causa do MPPI (achado 1), aplique a exceção de ajuste da Task 9 (valores de `MPPI_TUNING`/`CRITIC_TUNING`/`LOCAL_COSTMAP_SIZE`) e rode a varredura de novo.

- [ ] **Step 4: Registrar e derrubar tudo**

Acrescente ao `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md`:

```markdown
## Varredura dos 10 pontos

Comando: `python3 robot/scripts/nav_goal_sweep.py` com a simulação e o Nav2 da semana 3. Saída (colada de `geraldo-sweep.txt`):

<saída completa, uma linha por ponto, terminando em TODOS OS PONTOS OK ou FALHARAM: [...]>

Tentativas: <1 ou 2>. Duração total: <soma dos segundos>.
```

Derrube o Nav2 e a simulação pelos PIDs (`kill -9 -- -PID`) e confira que não sobrou `gz sim` seu (`ps -eo pid,pgid,cmd | grep "gz sim"`).

- [ ] **Step 5: Rodar tudo e commitar**

Run: `python3 -m pytest tools robot -q && source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q) && (cd robot/ros2_ws/src/geraldo_description && python3 -m pytest test -q)`
Expected: PASS nos três.

```bash
git add docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md
git commit -m "docs(robo): varredura dos 10 pontos a 3 m/s

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

Fim do plano 1. Avise o coordenador: (a) o relatório de medições e se algum cenário ficou NÃO SEGURO, (b) o contrato do estop da Task 1 está pronto para os planos 2, 3 e 4, (c) nada foi enviado com `push`.
