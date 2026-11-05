# G.E.R.A.L.D.O. — Plano de desenvolvimento (spec de design)

**Data:** 05/11/2026 · **Líder:** Samuel · **Status:** rascunho para revisão do líder

G.E.R.A.L.D.O. = **G**estor de **E**ntregas e **R**eposição **A**utônoma para **L**eitos e **D**ispensação **O**timizada.
Robô hospitalar autônomo que leva medicamentos e insumos da farmácia (e do banco de sangue) até os destinos, e que atualiza o estoque do hospital conforme transporta.

---

## 1. Objetivo e escopo

**Objetivo:** uma **demo integrada em simulação (Gazebo)** na ExpoTech, mostrando que um pedido feito no sistema hospitalar vira uma entrega autônoma, e que o estoque muda por causa do robô.

**Prazo:** 3 semanas a partir de 05/11/2026 (a data real da ExpoTech deve ser registrada aqui pelo líder).

**Dentro do escopo**
- Robô diferencial no Gazebo, navegando com Nav2 por um hospital inventado.
- Backend FastAPI com gestão hospitalar/estoque (padrão Command), JWT e papéis.
- Painel web simples (estoque por local, fila de entregas, histórico de movimentações).
- Pentest da API de despacho, com mitigação e relatório.
- Modelo 3D (Blender) e design system no repositório.

**Extras (cortados primeiro se o prazo apertar)**
- Cockpit Unity, inclusive no celular.
- Câmera RGB-D com leitura de marcador na chegada.

**Fora do escopo:** robô físico, dois andares reais (elevador), integração com sistemas hospitalares reais.

## 2. Equipe e papéis

| Pessoa | Frente | Entrega principal |
|---|---|---|
| Samuel (líder) | Integração, ambiente, 3D, guia das IAs, design system, Unity (extra) | Docker, `geraldo_description`, `hospital.yaml` e geradores, contratos, demo final |
| Erik | IMR (ROS 2, Gazebo, Nav2) | Controle, sensores, navegação, desvio, máquina de estados |
| Vieira | Backend (Paradigms) | API, domínio, estoque, fila, JWT, auditoria |
| Pedro | Painel web, depois Pentest e qualidade | Painel (semanas 1–2), ataques, relatório e testes (semana 3) |

## 3. O hospital (mundo da simulação)

Um andar, **46 × 30 m**, corredores de 2,0 m, portas de 1,0 m. Origem do referencial: canto sudoeste; x para leste, y para norte.

**Estrutura:** um anel externo de corredores mais uma cruz central (leste-oeste e norte-sul) formam 4 quarteirões e várias rotas entre quaisquer dois pontos.

| Quarteirão | Salas (x0, y0, x1, y1 em metros) |
|---|---|
| Noroeste | Farmácia central (2,16,12,28), Banco de sangue (12,22,22,28), Apoio/Rouparia (12,16,22,22) |
| Nordeste | Centro cirúrgico (24,16,34,28), UTI com 4 leitos (34,16,44,28) |
| Sudoeste | Pronto-socorro (2,8,22,14), Recepção (2,2,12,8), Consultório 1 (12,2,17,8), Consultório 2 (17,2,22,8) |
| Sudeste | Enfermaria 214 (24,2,34,14), Enfermaria 215 (34,2,44,14), 6 leitos e posto cada |

- Entrada principal na parede sul (x≈7); entrada de ambulância na parede oeste (y≈11).
- Salas grandes têm duas portas (uma por corredor vizinho), o que gera as rotas alternativas.
- **Cenário de demonstração de replanejamento:** banco de sangue → centro cirúrgico passa pelo corredor norte (~14 m); com uma maca bloqueando o corredor, o robô entra pela porta sul do centro cirúrgico via corredor central (~60 m).

### 3.1 `hospital.yaml` — fonte única

A planta é descrita **uma vez** em `hospital.yaml`; o script `tools/gen_hospital.py` gera:

| Saída | Consumidor |
|---|---|
| `worlds/hospital.sdf` (piso, paredes, portas como vãos) | Gazebo |
| `maps/hospital.pgm` + `.yaml` (ocupação, 5 cm) | Nav2 |
| `backend/seeds/locais.json` (cada sala é um `Local`) | Backend |
| `waypoints.yaml` (`local_id → x, y, yaw`) | `geraldo_dispatcher` |

Waypoints iniciais (estimativas, a ajustar quando o mundo existir):

| Waypoint | Sala | x, y (m) |
|---|---|---|
| `base_robo` | Farmácia (base de carga) | 6,5 · 26,5 |
| `farmacia_balcao` | Farmácia (retirada) | 7 · 24 |
| `banco_sangue_retirada` | Banco de sangue | 17 · 25 |
| `cc_entrega` | Centro cirúrgico | 29 · 25 |
| `uti_entrega` | UTI | 39 · 25 |
| `ps_entrega` | Pronto-socorro | 12 · 11 |
| `enf214_entrega` | Enf. 214 (posto) | 29 · 12 |
| `enf215_entrega` | Enf. 215 (posto) | 39 · 12 |
| `rouparia_coleta` | Apoio (rouparia) | 17 · 18,5 |

**Testes automáticos obrigatórios:** (1) todo waypoint cai em célula livre do mapa; (2) todo par de waypoints tem caminho entre si, e continua tendo com o corredor norte bloqueado.

Obstáculos dinâmicos (maca, pessoas circulando) ficam em `scenarios/*.yaml`, separados do mapa estático.

## 4. Funções do sistema

**Fluxo de uma entrega**

```
Prescrição (API) → Auth JWT → Command → Fila de prioridade → Reserva de estoque
 → Despacho ao robô → Nav2 navega e desvia → Chegada → Liberação da tampa
 → Baixa/crédito de estoque → Telemetria em todo o caminho
```

**Prioridades (do PDF do projeto)**

| Prioridade | Exemplo | Destino típico | Comportamento do robô | Validação |
|---|---|---|---|---|
| Crítica | Sangue, drogas de emergência | Centro cirúrgico, UTI, pronto-socorro | Rota mais curta, desvio mais agressivo de áreas de tráfego | JWT + assinatura dupla do farmacêutico |
| Média | Antibióticos, fluidos IV | Enfermarias 214/215 | Navegação padrão; aguarda liberação de corredor estreito | JWT do setor requisitante |
| Rotina | Inventário obsoleto, lençóis | Rouparia, farmácia | Só em horário de baixo pico; cede passagem a humanos | Log; permissões de baixo nível |

### 4.1 IMR — robô e navegação (Erik; Samuel no URDF e no mundo)
- Controle diferencial: `/cmd_vel` → rodas, com saturação proporcional (já feita na Aula 05).
- Sensores simulados: `/scan` (LiDAR 2D), 5 sensores de alcance (0°, ±45° frontais; ±135° traseiros; nenhum a 180°), câmera RGB-D.
- Nav2: rota global, costmap local, desvio reativo; footprint 0,70 × 0,50 m mais 10 cm de inflação.
- Máquina de estados: `IDLE → A_CAMINHO → CHEGOU → AGUARDANDO_RETIRADA → VOLTANDO`, mais `PARADA_EMERGENCIA` e `CARREGANDO`.
- Nó `geraldo_dispatcher`: consome a fila do backend e envia metas ao Nav2 usando `waypoints.yaml`.

### 4.2 Backend e gestão hospitalar (Vieira)
- Papéis: `medico`, `enfermeiro`, `farmaceutico`, `admin`, `robo`.
- Comandos (padrão Command): `CriarEntrega`, `CancelarEntrega`, `AprovarCritica`.
- Fila com 3 prioridades, FIFO dentro de cada uma.
- Estoque por local, alterado **somente** por `Movimentacao` (imutável, auditável).
- Cada entrega tem `origem` e `destino` (o banco de sangue é origem alternativa à farmácia).

### 4.3 Painel web (Pedro)
Três telas: (1) estoque por local, atualizado ao vivo; (2) fila e entregas em andamento, com prioridade e estado do robô; (3) histórico de movimentações. Consome só a API.

### 4.4 Pentest (Pedro)
Cinco ataques demonstráveis, com relatório antes/depois da mitigação e testes que travam regressão: requisição falsificada, JWT adulterado ou expirado, escalada de papel (enfermaria pedindo "crítica"), injeção nos campos, injeção de obstáculo falso na telemetria.

### 4.5 Cockpit Unity (extra, Samuel)
Lê a telemetria, desenha o robô (`.glb`), a rota e os obstáculos; desktop e celular.

## 5. Modelo de dados e regras de estoque

| Entidade | Para quê |
|---|---|
| `Usuario` | login e papel |
| `Local` | sala/ponto do hospital; vem do `hospital.yaml` |
| `Paciente` | ligado a um leito |
| `Medicamento`, `Lote` | item, validade, quantidade |
| `Estoque` | saldo por (item, local) |
| `Prescricao` | paciente, itens, prioridade, status |
| `Entrega` | pedido executado pelo robô: origem, destino, estado |
| `Movimentacao` | cada mudança de estoque; nunca editada |

| Evento da entrega | Efeito |
|---|---|
| Pedido aceito | Reserva na origem |
| Carga trancada no robô | Baixa na origem |
| Robô chega e entrega | Crédito no destino; prescrição vira `entregue` |
| Cancelamento ou falha | Estorno para a origem |

Locais com estoque: Farmácia central, Banco de sangue, UTI, Centro cirúrgico, Pronto-socorro, posto da Enf. 214, posto da Enf. 215.

## 6. Contratos entre as frentes

**Regra:** contratos ficam em `docs/contracts/`. Mudar um contrato exige PR e aviso ao dono da frente. A proposta abaixo é **travada na semana 1 (até domingo, 08/11)**, para o M1 de 11/11 não depender de contrato em aberto.

### 6.1 REST (backend)
| Método e rota | Papel | Função |
|---|---|---|
| `POST /auth/login` | todos | emite JWT |
| `POST /deliveries` | médico, enfermeiro, farmacêutico | cria entrega: `origin_id`, `dest_id`, `items[]`, `priority`, `prescription_id` |
| `GET /deliveries`, `GET /deliveries/{id}` | autenticado | consulta |
| `POST /deliveries/{id}/cancel` | solicitante, admin | cancela e estorna |
| `POST /deliveries/{id}/approve` | farmacêutico | assinatura dupla (crítica) |
| `GET /stock?location_id=` | autenticado | saldos |
| `GET /movements` | autenticado | histórico |
| `GET /locations` | autenticado | locais |
| `POST /robot/next-task` | robô | dispatcher pede a próxima entrega |
| `POST /robot/events` | robô | `LOADED`, `ARRIVED`, `UNLOCKED`, `FAILED` |
| `GET /telemetry` e `WS /ws/telemetry` | autenticado | pose, rota, obstáculos, bateria, estado |

### 6.2 ROS 2 (proposta)
Tópicos: `/cmd_vel`, `/odom`, `/scan`, `/range/front_c`, `/range/front_l45`, `/range/front_r45`, `/range/rear_l135`, `/range/rear_r135`, `/camera/color/image_raw`, `/camera/depth/image_raw`, `/geraldo/state`, `/geraldo/battery`. Navegação via ação `NavigateToPose` do Nav2.

### 6.3 JWT
Assinado, com `sub`, `role`, `exp`, `jti`. Segredo vem de variável de ambiente, nunca do repositório. O robô usa o papel `robo`.

## 7. Cronograma (3 semanas)

Semana 1 = 05–11/11 · Semana 2 = 12–18/11 · Semana 3 = 19–25/11.

| Marco | Data | Critério de pronto |
|---|---|---|
| M1 — fatia vertical | qua 11/11 | Pedido na API vira meta no Nav2 e o robô anda até um ponto no Gazebo |
| M2 — entrega completa | qua 18/11 | Pedido → reserva → robô entrega desviando obstáculo → estoque credita, visível no painel |
| M3 — demo congelada | qua 25/11 | Segurança integrada, demo ensaiada, vídeo de reserva gravado; só correção de bug depois |

| | Semana 1: fundação | Semana 2: profundidade | Semana 3: segurança e demo |
|---|---|---|---|
| Samuel | Repo, Docker, modelo e URDF v0, `hospital.yaml` e geradores, contratos, design system v0, guia das IAs | Mundo hospitalar completo, `geraldo_dispatcher` (com Erik), componentes do design system | Integração, congelamento, ensaio; Unity só se o M2 foi atingido |
| Erik | Robô no Gazebo, `/cmd_vel`, `/scan`, Nav2 básico | 5 sensores, desvio, máquina de estados, prioridades, parada de emergência | Ajuste fino, robustez, vídeo de reserva |
| Vieira | FastAPI, modelo de dados, JWT, criar entrega e fila (robô de mentira) | Movimentações, prescrições, assinatura dupla, auditoria, WebSocket | Endurecimento, correções do pentest |
| Pedro | Painel (esqueleto, API mock) | Painel com 3 telas ao vivo; scripts de ataque | 5 ataques, mitigação, relatório, testes, roteiro da demo |

**Ordem de corte:** (1) Unity no celular, (2) cockpit Unity, (3) câmera RGB-D e marcador, (4) assinatura dupla, (5) tela 3 do painel, (6) "rotina só em baixo pico", (7) pronto-socorro e Enf. 215.
**Não corta:** Gazebo + Nav2 + API + estoque mudando por causa do robô + pentest básico.

## 8. Modelo 3D e simulação

- Arquivos em `assets/blender/`: `geraldo2.blend`, `geraldo2.glb`, renders e `build_geraldo2.py` (o script gera tudo; cerca de 4 MB, sem Git LFS).
- Dimensões: chassi 0,70 × 0,50 m; rodas de tração 0,20 m (eixo em x = +0,10 m, mais à frente para estabilidade, com separação de 0,45 m); rodízio traseiro 0,08 m; baú 0,48 × 0,40 m; altura total 0,47 m.
- O Gazebo **não usa o `.blend`**: usa uma malha visual exportada (`.dae` ou `.stl`) e uma colisão simples de 0,70 × 0,50 m, com URDF escrito à mão em `ros2_ws/src/geraldo_description/`.
- O LiDAR do modelo é um disco opcional no topo; no URDF o sensor existe independentemente do visual.
- **Ambiente:** o grupo mistura Windows, Mac e Linux. Imagem Docker única com ROS 2 + Gazebo + Nav2. Gazebo **headless** para desenvolver; a demo roda na máquina Linux do líder.
- Versão do ROS 2 e do Gazebo a confirmar com o que a disciplina usa (recomendação: Jazzy + Gazebo Harmonic).

## 9. Guia para as IAs do grupo

| Arquivo | Função |
|---|---|
| `AGENTS.md` (raiz) | Fonte única: visão, mapa de pastas, regras, contratos, como rodar e testar, definição de pronto |
| `CLAUDE.md`, `.github/copilot-instructions.md` | Apontam para `AGENTS.md` |
| `<pasta>/AGENTS.md` | Regras de `backend/`, `ros2_ws/`, `unity/`, `security/`, `web/` |
| `docs/prompts/00-inicio-<papel>.md` | Prompt de partida por papel |

**Regras duras (no `AGENTS.md`):** contrato primeiro (mudança só via PR em `docs/contracts/`); estoque só por `Movimentacao`; todo código novo com teste; nada na `main` (branch `feat/<frente>-<assunto>` e PR); nenhum segredo no repositório; na dúvida, perguntar antes de inventar.

**Formato dos prompts:** contexto → minha frente → tarefa da semana → o que não tocar → "diga o plano antes de agir".
Documentos em português; comandos, pastas e código em inglês.

## 10. Design system (subprojeto separado)

Terá spec própria. Segue a estrutura do `DESIGN_SYSTEM.md` do barberschedule (marca, regras de ouro, paleta, tipografia, espaçamento, componentes base e de domínio) com tokens em `tokens.json` que geram CSS variables, preset Tailwind e cores para o Unity. Componentes de domínio previstos: `PriorityBadge`, `RobotStatusCard`, `StockLevelBar`, `DeliveryQueueRow`, `MovementLogRow`, `AlertBanner`, `TelemetryPanel`. A direção visual depende das referências hospitalares que o líder vai fornecer; a v0 sai na semana 1.

## 11. Riscos e decisões abertas

| Item | Decisão ou risco | Dono |
|---|---|---|
| Altura do robô | Imagens de referência dão 0,47 m; o texto de requisitos pede 0,90–1,00 m. Foi seguido o modelo das imagens; variante alta só se o líder pedir | Samuel |
| Versão ROS 2/Gazebo | Confirmar com a disciplina | Samuel e Erik |
| Gazebo com GUI em Windows/Mac | Mitigado com headless e demo no Linux do líder | Samuel |
| Data real da ExpoTech | Registrar na seção 1 | Samuel |
| LiDAR no topo | Presente no modelo por sugestão da especificação; pode sair com `LIDAR = False` em `build_geraldo2.py` | Samuel |
| Pedro depende da API | Mitigado: painel contra API mock nas semanas 1–2 | Pedro e Vieira |
| Erik é o caminho crítico do IMR | Samuel absorve URDF, mundo e geradores para aliviar | Samuel |
