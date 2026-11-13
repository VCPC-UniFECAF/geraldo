# Semana 3 completa: robô, backend, web e app instalável

**Data:** 13/11/2026 · **Dono:** Samuel (executa também o que era do Erik e do Vieira) · **Base:** [plano de desenvolvimento](2026-11-05-geraldo-plano-desenvolvimento-design.md) (seções 4, 6 e 7), [semana 2 do robô](2026-11-13-semana2-robo-design.md) e os planos da semana 1 ([Erik](../plans/2026-11-05-semana1-erik-backend.md), [Vieira](../plans/2026-11-05-semana1-vieira-web.md), [Pedro](../plans/2026-11-05-semana1-pedro-qualidade.md)).
**Prazo:** M2 qua 18/11 · M3 (congelamento) qua 25/11 · ensaio qui 26 e sex 27/11 · ExpoTech sáb 28/11.

## 1. Estado de partida (verificado em 13/11, `main` em `d81ab13`)

- **Robô:** dispatcher com máquina de estados, prioridades (perfil de velocidade e de inflação), emergência por tópico, telemetria, 5 sensores de alcance, hospital 3D, 197 testes na raiz, 67 no dispatcher e 28 no description.
- **Backend:** **não existe.** `backend/` só tem `AGENTS.md` e `seeds/locais.json`. Nenhuma branch do Erik foi publicada.
- **Web:** semana 1 do Vieira pronta (login, solicitar, minhas entregas, componentes base e a API simulada com MSW). A aba Estoque diz "Em breve". Não há nada do robô.
- **Pedro:** `tools/` só tem testes de layout e de contrato; **`tools/mock_robot.py` não existe.**
- **Contrato:** `docs/contracts/openapi.yaml` já tem `POST /robot/telemetry`, `GET /deliveries/{id}` para o `robo` e o `Telemetry` com `obstacles`.

## 2. Objetivo

Todas as frentes no nível da semana 3, sem parar nas semanas 1 e 2: o pedido feito no sistema vira entrega autônoma e o estoque muda por causa do robô, visível no painel; e o mesmo sistema roda como **aplicativo local instalável** que sobe a simulação e a mostra na janela.

## 3. Decisões (aprovadas por Samuel em 13/11)

| Tema | Decisão | Por quê |
|---|---|---|
| Velocidade | **3,0 m/s sempre** (cerca de 10 km/h). Saem o `/speed_limit` fixo e a velocidade dos perfis de prioridade | Pedido do líder. Sobrepõe a regra "1,0 m/s é o teto" do `robot/AGENTS.md`, que deve ser reescrita |
| Prioridade | Só o raio de inflação do costmap local muda: crítica 0,55 m, média e rotina 0,70 m | Mantém o "desvio mais agressivo" da crítica sem limitar velocidade |
| Curvas | Um nó lê o `/plan`, calcula a curvatura à frente e publica o limite pelo `/speed_limit` do Nav2. `v = min(3,0; √(a_lat / curvatura))`, `a_lat` = 1,0 m/s² (configurável) | Desaceleração em curvas e portas sem trocar de controlador. Função pura e testável |
| Se 3 m/s não for seguro | O implementador **reporta o número medido** (frenagem, desvio da maca, curva) e propõe limite por trecho. Não decide sozinho | O hospital tem corredores de 2 m, portas de 1 m e sensores de 2 m |
| Obstáculos | Detecção real: `/scan` → pontos no mapa pela pose do AMCL → descarta o que bate com o mapa estático → agrupa por proximidade → até 20 `{x, y, radius}` em `obstacles` da telemetria | Hoje `obstacles` é sempre `[]` |
| Emergência pelo painel | Contrato novo: `POST /robot/estop` (admin, farmacêutico; corpo `{active: bool}`) e `GET /robot/estop` (robo; a cada 1 s). O robô junta backend e tópico `/geraldo/estop`; só sai da parada com as duas fontes desligadas | O painel precisa do botão sem ROS |
| Câmera RGB-D | Sensor e ponte em `/camera/color/image_raw` e `/camera/depth/image_raw`. **Sem leitura de marcador** (corte 3 da spec original) | Contrato de tópicos já existe |
| Backend | FastAPI, SQLModel com SQLite, PyJWT HS256, Command, Strategy, Factory, Observer. Cobre os planos da semana 1 e as semanas 2 e 3 da spec original, mais endurecimento | Não existe código |
| Pedro | Só o que destrava: `tools/mock_robot.py` e o teste de contrato do backend (`backend/tests/test_contract.py`). 5 ataques, pentest e relatório ficam com o Pedro | Decisão do líder |
| Web | Tudo da semana 1 ao nível da 3: confirmar recebimento, estoque, fila com estado do robô, histórico, ao vivo pelo WebSocket, botão de emergência, celular | Pedido do líder |
| App local | **Electron** (`.AppImage` e `.deb`) com o `web/` inteiro. Ao abrir: confere o ambiente, sobe backend, Gazebo, Nav2 e dispatcher, e mostra a simulação | Escolha do líder |
| Simulação visível | **Visão 2D própria** (hospital, robô, rota, obstáculos, sensores ao vivo) + botão que abre o Gazebo 3D | Escolha do líder; não depende de embutir janela |
| Ponte ROS do app | Pacote `geraldo_bridge` em `rclpy` + FastAPI, escuta só em `127.0.0.1`, só fala os tópicos que o app usa (nada de `rosbridge`, que não está instalado e expõe `/cmd_vel`) | Segurança e tipos |
| ROS e Gazebo | **Não vão dentro do instalável.** O app usa o ROS 2 Jazzy e o Gazebo Harmonic da máquina e diz o que falta. O backend roda com o Python do sistema num venv criado na primeira execução | Não dá para empacotar ROS |

## 4. Subprojetos e ordem

Quatro planos, executados em ordem, numa **cadeia de branches** (cada uma parte da anterior; um PR por branch; nada na `main`):

| # | Plano | Branch | Entrega |
|---|---|---|---|
| 1 | [Contrato e robô](../plans/2026-11-13-semana3-1-contrato-robo.md) | `feat/semana3-robo` | Contrato do estop; 3 m/s; desaceleração em curvas; obstáculos reais; estop pelo backend no dispatcher; câmera RGB-D; script e roteiro da demo |
| 2 | [Backend](../plans/2026-11-13-semana3-2-backend.md) | `feat/semana3-backend` | FastAPI completo; `tools/mock_robot.py`; teste de contrato |
| 3 | [Web](../plans/2026-11-13-semana3-3-web.md) | `feat/semana3-web` | Telas e componentes que faltam, ao vivo, botão de emergência |
| 4 | [App instalável](../plans/2026-11-13-semana3-4-app.md) | `feat/semana3-app` | Ponte ROS, orquestrador, Electron, visão 2D, pacotes |

A branch `docs/semana3-spec-planos` (este spec e os planos) é a base da cadeia. O plano 2 reaproveita por referência o plano do Erik da semana 1 (`2026-11-05-semana1-erik-backend.md`, tarefas 1 a 5, que já traz o código completo) e acrescenta o resto.

## 5. Contratos novos (tudo em `docs/contracts/`, PR antes do código que os usa)

- `openapi.yaml`: `POST /robot/estop` (papéis `admin` e `farmaceutico`; corpo `{active: boolean}`; `204`, `401`, `403`, `422`) e `GET /robot/estop` (papel `robo`; `200` com `{active: boolean}`, `401`, `403`).
- `ros-interfaces.md`: o dispatcher lê o estop do backend; câmera RGB-D nos tópicos já listados; `geraldo_bridge` publica/assina só `/geraldo/estop`, `/geraldo/state`, `/geraldo/battery`, `/amcl_pose`, `/plan`, `/scan` e `/range/*`.
- `robot-protocol.md`: cadência do `GET /robot/estop` (1 s), regra de junção das duas fontes de emergência e o formato de `obstacles`.
- Os exemplos em `docs/contracts/examples/` são regenerados por `robot/scripts/contract_examples.py`.

## 6. Restrições globais (valem para todos os planos)

- **AGENTS.md:** contrato primeiro; nenhum segredo no repositório; nada direto na `main`; todo código novo com teste; texto de interface em português; padrões em `docs/padroes-de-projeto.md` (injeção pelo construtor, Strategy/Factory no lugar de `if/elif` por tipo, funções puras).
- **Commits:** em português, `tipo: o que mudou`, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Descrições de PR terminam com `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **ROS e Gazebo:** todo comando de simulação com `ROS_DOMAIN_ID=77` e `GZ_PARTITION=verif` (outra sessão pode estar rodando; não a toque). Nunca `pkill -f` nem `pgrep -f` (derrubam o próprio shell): usar PID. `gz sim` e o dispatcher exigem `kill -9`.
- **Git:** nunca `git stash` solto; caminhos absolutos do worktree; nada de `push` nem de PR sem o líder.
- **Design system (web e app):** sem hex solto; vermelho só para prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro; um botão primário por tela; alvo de toque mínimo de 44 px; números com `tabular-nums`; ícones `lucide-react`; texto em português, *sentence case*.
- **Backend:** JWT só HS256, exigindo `exp`, `sub`, `role` e `jti`; segredo em `GERALDO_JWT_SECRET`; estoque só por `Movimentacao`; prioridade `critica` < `media` < `rotina`, FIFO por `id`; mensagens de erro em português no formato "o que houve + o que fazer".
- **Versões:** Python 3.12 (3.11+ no backend), ROS 2 Jazzy, Gazebo Harmonic 8, Node 24, React 19, Vite 8, Tailwind v3, Electron (última estável de pelo menos 2 semanas).

## 7. Verificação (o que conta como pronto)

- `python3 -m pytest tools robot -q` verde; testes de cada pacote ROS; `backend`: `python -m pytest -q`; `web`: `npm test -- --run` e `npm run build`.
- **Robô a 3 m/s:** teste de frenagem em corredor reto, curva de 90° e desvio da maca, com os números no relatório; varredura dos 10 pontos no hospital 3D com o `TODOS OS PONTOS OK`.
- **Ponta a ponta:** pedido na web → reserva → robô entrega (simulação) → confirmar recebimento → estoque credita, visível no painel; botão de emergência para o robô.
- **App:** `.AppImage` e `.deb` gerados; abrir o app numa máquina com ROS sobe o stack e mostra o robô se mexendo na visão 2D.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| 3 m/s em corredores de 2 m e portas de 1 m | Teste de frenagem e desvio; relatar o número real e propor limite por trecho |
| Sem backend de ninguém, o M2 depende deste trabalho | Ordem 1 → 2 → 3 → 4; o app só começa com backend e web de pé |
| Erik e Vieira podem mexer em `backend/` e `web/` ao mesmo tempo | Samuel avisa os dois; a cadeia de branches isola o trabalho |
| `rclpy` só roda com o ROS carregado | Testes da ponte com `FakeRosPort`; teste real só no fim, com a simulação |
| Electron baixa ~100 MB na primeira instalação | Esperado; versão fixa no `package-lock.json` |
| Outra sessão usa a mesma máquina e o Gazebo | Domínio ROS isolado (77) e partição Gazebo `verif` |

## 9. Fora do escopo

Unity, Docker, leitura de marcador na câmera, modo manual (teleop), vídeo de reserva (o líder grava), 5 ataques e relatório do Pedro, e qualquer push, PR ou merge sem o líder.
