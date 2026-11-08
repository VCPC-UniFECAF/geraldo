# G.E.R.A.L.D.O. — Plano de desenvolvimento (spec de design)

**Data:** 05/11/2026 · **Líder:** Samuel · **Status:** rascunho para revisão do líder

G.E.R.A.L.D.O. = **G**estor de **E**ntregas e **R**eposição **A**utônoma para **L**eitos e **D**ispensação **O**timizada.
Robô hospitalar autônomo que leva medicamentos e insumos da farmácia (e do banco de sangue) até os destinos, e que atualiza o estoque do hospital conforme transporta.

---

## 1. Objetivo e escopo

**Objetivo:** uma **demo integrada em simulação (Gazebo)** na ExpoTech, mostrando que um pedido feito no sistema hospitalar vira uma entrega autônoma, e que o estoque muda por causa do robô.

**Prazo:** ExpoTech no **sábado, 28/11/2026**. O desenvolvimento ocupa 3 semanas (05–25/11), com o congelamento (M3) na quarta 25/11 e quinta e sexta (26 e 27/11) reservadas a ensaio e imprevistos.

**Dentro do escopo**
- Robô diferencial no Gazebo, navegando com Nav2 por um hospital inventado.
- Backend FastAPI com gestão hospitalar/estoque (padrão Command), JWT e papéis.
- Sistema web (prioridade) usado pelos profissionais: solicitar medicamentos do próprio consultório, acompanhar a entrega e confirmar o recebimento; mais painel de estoque, fila e histórico. Responsivo: usável no computador e no navegador do celular (sem app nativo).
- Pentest da API de despacho, com mitigação e relatório.
- Modelo 3D (Blender) e design system no repositório.

**Extras (cortados primeiro se o prazo apertar)**
- Cockpit Unity, inclusive no celular.
- Câmera RGB-D com leitura de marcador na chegada.

**Fora do escopo:** robô físico, dois andares reais (elevador), integração com sistemas hospitalares reais.

## 2. Equipe e papéis

| Pessoa | Frente | Entrega principal |
|---|---|---|
| Samuel (líder) | Robô e simulação (IMR), hospital, 3D, ambiente, contratos, guia das IAs, tokens do design system, Unity (extra) | Docker, `geraldo_description` (URDF), mundo Gazebo, `hospital.yaml` e geradores, sensores, Nav2, máquina de estados, `geraldo_dispatcher`, demo final |
| Erik | Backend e gestão hospitalar (Paradigms) | API, domínio, estoque, fila, JWT, auditoria, endpoints do robô, WebSocket |
| Vieira | Sistema web responsivo | Telas de solicitar e acompanhar entrega, painel (estoque, fila, histórico), dados de demo, componentes do design system |
| Pedro | Qualidade e segurança (Pentest) | Robô de mentira (mock do dispatcher), CI, testes de contrato, 5 ataques, mitigação e relatório |

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
| `cons1_entrega` | Consultório 1 | 14,5 · 4 |
| `cons2_entrega` | Consultório 2 | 19,5 · 4 |

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

### 4.1 IMR — robô e navegação (Samuel)
- Controle diferencial: `/cmd_vel` → rodas, com saturação proporcional (já feita na Aula 05).
- Sensores simulados: `/scan` (LiDAR 2D), 5 sensores de alcance (0°, ±45° frontais; ±135° traseiros; nenhum a 180°), câmera RGB-D.
- Nav2: rota global, costmap local, desvio reativo; footprint 0,70 × 0,50 m mais 10 cm de inflação.
- Máquina de estados: `IDLE → A_CAMINHO → CHEGOU → AGUARDANDO_RETIRADA → VOLTANDO`, mais `PARADA_EMERGENCIA` e `CARREGANDO`.
- Nó `geraldo_dispatcher`: consome a fila do backend e envia metas ao Nav2 usando `waypoints.yaml`.

### 4.2 Backend e gestão hospitalar (Erik)
- Papéis: `medico`, `enfermeiro`, `farmaceutico`, `admin`, `robo`.
- Comandos (padrão Command): `CriarEntrega`, `CancelarEntrega`, `AprovarCritica`.
- Fila com 3 prioridades, FIFO dentro de cada uma.
- Estoque por local, alterado **somente** por `Movimentacao` (imutável, auditável).
- Cada entrega tem `origem` e `destino` (o banco de sangue é origem alternativa à farmácia).

### 4.3 Painel web (Vieira)
Usado pelos profissionais no computador (prioridade) e no navegador do celular (mesma base, layout responsivo; a tela de solicitar é pensada mobile-first). Consome só a API.

1. **Solicitar medicamento:** itens e quantidade, prioridade, destino padrão = local do usuário (o consultório ou posto onde ele trabalha), com o saldo da origem visível.
2. **Minhas entregas:** acompanhamento em tempo real e **confirmação de recebimento**, que libera a tampa do robô.
3. **Estoque por local**, atualizado ao vivo.
4. **Fila e entregas em andamento** (visão da farmácia e do admin), com prioridade e estado do robô.
5. **Histórico de movimentações.**

### 4.4 Pentest (Pedro)
Cinco ataques demonstráveis, com relatório antes/depois da mitigação e testes que travam regressão: requisição falsificada, JWT adulterado ou expirado, escalada de papel (enfermaria pedindo "crítica"; outro usuário confirmando o recebimento de uma entrega alheia), injeção nos campos, injeção de obstáculo falso na telemetria.

### 4.5 Cockpit Unity (extra, Samuel)
Lê a telemetria, desenha o robô (`.glb`), a rota e os obstáculos; desktop e celular.

## 5. Modelo de dados e regras de estoque

| Entidade | Para quê |
|---|---|
| `Usuario` | login, papel e `local_id` (consultório ou posto onde trabalha) |
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
| Robô chega ao destino | Entrega fica `AGUARDANDO_RECEBIMENTO` |
| Solicitante confirma o recebimento no sistema | Tampa é liberada; crédito no destino; prescrição vira `entregue` |
| Cancelamento ou falha | Estorno para a origem |

Locais com estoque: Farmácia central, Banco de sangue, UTI, Centro cirúrgico, Pronto-socorro, posto da Enf. 214, posto da Enf. 215, Consultório 1 e Consultório 2 (consumíveis).

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
| `POST /deliveries/{id}/confirm-receipt` | solicitante da entrega | confirma o recebimento; libera a tampa |
| `GET /me` | autenticado | usuário, papel e `local_id` (destino padrão dos pedidos) |
| `GET /stock?location_id=` | autenticado | saldos (com `item_name`, para a web listar os itens) |
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
| Ensaio e folga | qui 26 e sex 27/11 | Ensaio completo na máquina da demo, ajustes de roteiro, nenhuma funcionalidade nova |
| ExpoTech | sáb 28/11 | Apresentação |

| | Semana 1: fundação | Semana 2: profundidade | Semana 3: segurança e demo |
|---|---|---|---|
| Samuel | Repo, ambiente ROS nativo, modelo e URDF v0, `hospital.yaml` e geradores, robô no Gazebo com `/cmd_vel` e `/scan`, Nav2 básico, `geraldo_dispatcher` mínimo, contratos, guia das IAs, tokens do design system | Mundo hospitalar completo, 5 sensores, desvio, máquina de estados, prioridades, parada de emergência, `geraldo_dispatcher` completo (eventos e estados) | Integração, ajuste fino do robô, vídeo de reserva, congelamento, ensaio; Unity só se o M2 foi atingido |
| Erik | FastAPI, modelo de dados, JWT, criar entrega e fila | Movimentações de estoque, prescrições, assinatura dupla, auditoria, endpoints do robô, WebSocket | Endurecimento, correções do pentest |
| Vieira | Telas de solicitar e minhas entregas (mobile-first, sobre API mock), componentes do design system | Confirmar recebimento, painel de estoque, fila e histórico ao vivo, dados de demo | Polimento, teste no celular, apoio ao roteiro da demo |
| Pedro | Robô de mentira (mock do dispatcher), CI, coleção de requests da API | Scripts de ataque, testes de contrato | 5 ataques, mitigação, relatório, testes, roteiro da demo |

**Ordem de corte:** (1) Unity no celular, (2) cockpit Unity, (3) câmera RGB-D e marcador, (4) assinatura dupla, (5) tela de histórico de movimentações, (6) "rotina só em baixo pico", (7) pronto-socorro e Enf. 215.
**Não corta:** Gazebo + Nav2 + API + estoque mudando por causa do robô + pentest básico.

## 8. Modelo 3D e simulação

- Arquivos em `modelos-3d/`: `geraldoV1.blend`, `geraldoV1.glb`, renders e `build_geraldoV1.py` (o script gera tudo; cerca de 4 MB, sem Git LFS).
- Dimensões: chassi 0,70 × 0,50 m; rodas de tração 0,20 m (eixo em x = +0,10 m, mais à frente para estabilidade, com separação de 0,45 m); rodízio traseiro 0,08 m; baú 0,48 × 0,40 m; altura total 0,47 m.
- O Gazebo **não usa o `.blend`**: usa uma malha visual exportada (`.dae` ou `.stl`) e uma colisão simples de 0,70 × 0,50 m, com URDF escrito à mão em `ros2_ws/src/geraldo_description/`.
- O LiDAR do modelo é um disco opcional no topo; no URDF o sensor existe independentemente do visual. No Gazebo o campo de visão é de cerca de 172° (o baú bloqueia a traseira); a traseira passa a ser coberta pelos 2 sensores de proximidade a ±135° na semana 2.
- **Ambiente:** o robô roda **nativo** na máquina Linux do líder (Pop!_OS 24.04 com ROS 2 Jazzy e Gazebo Harmonic), que também é a máquina da demo. Os outros três não precisam de ROS: o backend e a web não dependem do Gazebo e o Pedro usa o robô de mentira. Gazebo **headless** para desenvolver. Uma imagem Docker (ROS 2 + Gazebo + Nav2) fica como tarefa opcional da semana 2, para rodar o robô em outra máquina ou no CI.
- Versão do ROS 2 e do Gazebo a confirmar com o que a disciplina usa (recomendação: Jazzy + Gazebo Harmonic).

## 9. Guia para as IAs do grupo

| Arquivo | Função |
|---|---|
| `AGENTS.md` (raiz) | Fonte única: visão, mapa de pastas, regras, contratos, como rodar e testar, definição de pronto |
| `CLAUDE.md`, `.github/copilot-instructions.md` | Apontam para `AGENTS.md` |
| `<pasta>/AGENTS.md` | Regras de `backend/`, `ros2_ws/`, `unity/`, `security/`, `web/` |
| `docs/prompts/00-inicio-<papel>.md` | Prompt de partida por papel |

**Regras duras (no `AGENTS.md`):** contrato primeiro (mudança só via PR em `docs/contracts/`); estoque só por `Movimentacao`; todo código novo com teste; nada na `main` (branch `feat/<frente>-<assunto>` e PR); nenhum segredo no repositório; na dúvida, perguntar antes de inventar.

**Padrão de código (adotado em 08/11):** o código segue os conceitos da disciplina Programming Paradigms (SOLID, Factory Method, Strategy, Builder, Observer, Adapter, injeção de dependência e funções puras), detalhados em `docs/padroes-de-projeto.md`. Regra: padrão só onde há variação real.

**Formato dos prompts:** contexto → minha frente → tarefa da semana → o que não tocar → "diga o plano antes de agir".
Documentos em português; comandos, pastas e código em inglês.

## 10. Design system (subprojeto separado)

Tem spec própria: [2026-11-05-geraldo-design-system-design.md](2026-11-05-geraldo-design-system-design.md). Segue a estrutura do `DESIGN_SYSTEM.md` do barberschedule (marca, regras de ouro, paleta, tipografia, espaçamento, componentes base e de domínio) com tokens em `tokens.json` que geram CSS variables, preset Tailwind e cores para o Unity. Componentes de domínio previstos: `PriorityBadge`, `StatusBadge`, `StatCard`, `RobotStatusCard`, `DeliveryQueueRow`, `StockLevelBar`, `MovementLogRow`, `AlertBanner`, `TelemetryPanel`, `RequestForm`.

**Direção visual (aprovada pelo líder):** base branca, azul e vermelha. Azul primário `#3A66E8`; vermelho `#D92D3A` só para prioridade crítica, perigo, parada de emergência e estoque abaixo do mínimo; verde e âmbar só como feedback. Prioridades: crítica = vermelho, média = azul, rotina = cinza. Cards brancos de 16 px sobre fundo `#F4F6FB`, borda fina e sombra suave; fontes Plus Jakarta Sans (títulos e números grandes) e Inter (corpo e tabelas), números tabulares; sem modo escuro na v1. Web responsivo (computador e celular), alvos de toque de 44 px. As referências fornecidas pelo líder são só inspiração visual (sem chat nem perfil de paciente). A v0 sai na semana 1.

## 11. Riscos e decisões abertas

| Item | Decisão ou risco | Dono |
|---|---|---|
| Altura do robô | Imagens de referência dão 0,47 m; o texto de requisitos pede 0,90–1,00 m. Foi seguido o modelo das imagens; variante alta só se o líder pedir | Samuel |
| Versão ROS 2/Gazebo | Confirmar com a disciplina | Samuel |
| Gazebo com GUI em Windows/Mac | Mitigado com headless e demo no Linux do líder | Samuel |
| LiDAR no topo | Presente no modelo por sugestão da especificação; pode sair com `LIDAR = False` em `build_geraldoV1.py` | Samuel |
| Frontend (Vieira) ganhou escopo: solicitar e confirmar recebimento | Prioridade do sistema web; corta-se primeiro a tela de histórico e depois a de fila | Vieira e Samuel |
| Stack do app web | Vieira decide até 07/11 (recomendação: React + Vite + TypeScript + Tailwind v3); os tokens do design system valem em qualquer stack | Vieira |
| Pentest depende da API pronta | Pedro prepara os scripts contra API mock nas semanas 1–2 e ataca a API real na semana 3 | Pedro e Erik |
| Samuel acumula liderança e robô (caminho crítico) | Backend e painel não dependem do robô (robô de mentira do Pedro); contratos travados cedo; o Unity é o primeiro corte | Samuel |
