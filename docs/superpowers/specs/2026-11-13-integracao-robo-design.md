# Integração do robô com o backend (Erik), a web (Vieira) e o robô de mentira (Pedro)

**Data:** 13/11/2026 · **Dono:** Samuel · **Base:** planos da semana 1 do Erik, do Vieira e do Pedro, `docs/contracts/` e o `geraldo_dispatcher` desta branch.

## 1. O que cada frente espera do robô

| Frente | O que o plano dela usa do robô | Estado hoje |
|---|---|---|
| Erik (backend) | `POST /robot/next-task` (papel `robo`, usuário semeado `robo`, senha em `GERALDO_DEMO_PASSWORD`); semana 2: `POST /robot/events`, telemetria, WebSocket | Dispatcher chama `next-task`, manda os eventos e a telemetria. Seeds `backend/seeds/locais.json` batem com `waypoints.yaml` (gerados pelo mesmo `gen_hospital.py`) |
| Vieira (web) | Semana 1 só usa API simulada (MSW). Semana 2: estado do robô, fila e confirmar recebimento ao vivo | Falta fixture realista de telemetria e eventos para as telas e o MSW |
| Pedro (qualidade) | `tools/mock_robot.py` imita o dispatcher (`next-task`, depois `events`); ataque "obstáculo falso na telemetria" | O mock não tem um protocolo escrito para seguir; o teste de contrato dele precisa conhecer a operação nova `POST /robot/telemetry` |

## 2. Lacunas encontradas

1. **O `robo` não consegue ler a entrega.** No plano do Erik, `GET /deliveries/{id}` só devolve a entrega ao solicitante e a `SEE_ALL = (admin, farmaceutico)`; para o `robo` seria 404. O dispatcher espera o recebimento por esse endpoint (`AGUARDANDO_RETIRADA` até `ENTREGUE`), então todas as entregas terminariam em `FAILED` após 5 minutos.
2. **Falha do backend derruba o robô.** Um erro HTTP ou o backend reiniciando (`uvicorn --reload`) levanta exceção sem tratamento e encerra o nó do dispatcher no meio da entrega.
3. **Nada garante que seeds e waypoints continuam batendo.** Hoje batem por serem gerados juntos; ninguém testa.
4. **Sem exemplos reais.** Vieira e Pedro vão inventar corpos de telemetria e de eventos; qualquer diferença do que o robô envia só aparece na integração.
5. **Protocolo só no código.** A ordem dos eventos, a cadência e a tolerância a falhas não estão escritas em lugar nenhum para o Erik, o Vieira e o Pedro.

## 3. Decisões

| # | Decisão |
|---|---|
| 1 | Contrato: `GET /deliveries/{id}` ganha a regra "o papel `robo` pode consultar qualquer entrega (somente leitura)". Aviso ao Erik no protocolo. Commit isolado `docs(contratos)` para virar PR de contrato |
| 2 | `BackendError` (herda de `RuntimeError`) é o único erro que o `BackendClient` deixa subir: HTTP diferente de 401/409 e backend fora do ar. O dispatcher reenvia evento até 3 vezes (1 s entre as tentativas) e segue com a entrega; a espera do recebimento trata erro de consulta como "ainda não" até o timeout; o laço do nó e o login inicial esperam o backend voltar. Senha errada (401 no login) continua sendo erro fatal |
| 3 | Teste: todo `waypoint` das seeds existe em `waypoints.yaml` e todo waypoint (menos `base_robo`) tem um local |
| 4 | Exemplos em `docs/contracts/examples/robot-telemetry.json` (um por estado) e `robot-events.json` (4 cenários), **gerados do código** por `robot/scripts/contract_examples.py` e validados contra o OpenAPI por um validador mínimo (`robot/scripts/openapi_check.py`, sem dependência nova). Teste falha se os arquivos ficarem velhos |
| 5 | `docs/contracts/robot-protocol.md`: sequência, cadências, falhas, emergência e os avisos para Erik, Vieira e Pedro |

## 4. Fora do escopo

- `obstacles` da telemetria segue `[]` (o robô ainda não detecta obstáculos por conta própria); o campo existe para o cockpit e fica para a semana 3.
- Tarefa inválida (waypoint ou prioridade desconhecida) continua levantando erro; o contrato fixa os valores e as seeds são geradas.
- Reenvio de eventos perdidos depois das 3 tentativas.
- Botão de emergência no painel (precisa de contrato novo, semana 3).
