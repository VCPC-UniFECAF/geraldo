# Protocolo do robô (`geraldo_dispatcher` ↔ backend)

Complementa `openapi.yaml` e `ros-interfaces.md`: não cria endpoint nem tópico, só diz **em que ordem e com que cadência** o robô os usa. Os exemplos reais estão em `docs/contracts/examples/` e são gerados do código por `python3 robot/scripts/contract_examples.py` (um teste falha se ficarem velhos ou deixarem de seguir o OpenAPI).

## 1. Quem fala com quem

- O `geraldo_dispatcher` (Samuel) entra no backend (Erik) com o usuário `robo` e fala com ele por HTTP; fala com o Nav2 por ROS.
- O painel web (Vieira) e o robô de mentira (Pedro) só leem este protocolo e os exemplos.
- Senha do robô: `GERALDO_ROBOT_PASSWORD` (ou `GERALDO_DEMO_PASSWORD`); URL: `GERALDO_API_URL` (padrão `http://localhost:8000`).

## 2. Sequência de uma entrega

| # | Estado do robô | Chamada ao backend |
|---|---|---|
| 1 | `IDLE` | `POST /robot/next-task`: `200` com `RobotTask` (a entrega já vira `EM_ROTA`) ou `204` se a fila está vazia; repete a cada 2 s |
| 2 | `A_CAMINHO` (até `origin_waypoint`) | — |
| 3 | `CARREGANDO` | `POST /robot/events` com `LOADED` |
| 4 | `A_CAMINHO` (até `dest_waypoint`) | — |
| 5 | `CHEGOU` | `POST /robot/events` com `ARRIVED` |
| 6 | `AGUARDANDO_RETIRADA` | `GET /deliveries/{id}` a cada 2 s até o status ser `ENTREGUE` (o solicitante chama `POST /deliveries/{id}/confirm-receipt`) |
| 7 | `AGUARDANDO_RETIRADA` | `POST /robot/events` com `UNLOCKED`, **depois** do `ENTREGUE` |
| 8 | `VOLTANDO` (até `base_robo`) | — |
| 9 | `IDLE` | volta ao passo 1 |

O perfil de navegação segue a `priority` da tarefa: `critica` 1,0 m/s, `media` 0,8 m/s, `rotina` 0,5 m/s (e raio de inflação do costmap local de 0,55 m para `critica`, 0,70 m para as outras).

## 3. Falhas

O robô manda `FAILED` com `reason` e depois volta à base (`VOLTANDO` → `IDLE`):

| `reason` | Quando |
|---|---|
| `não chegou à origem` / `não chegou ao destino` | o Nav2 não completou a meta |
| `entrega cancelada` / `entrega falhou` | o status virou `CANCELADA` ou `FALHOU` durante a espera |
| `recebimento não confirmado a tempo` | 300 s sem `ENTREGUE`; ganha o sufixo `(<erro>)` se as consultas falharam |
| `local sem ponto de parada (waypoint nulo)...` / `waypoint desconhecido: ...` / `Prioridade desconhecida: ...` | a tarefa chegou com dado que o robô não sabe executar; ele não sai do lugar |

O backend pode responder `409` a um evento (por exemplo `FAILED` de uma entrega já cancelada): o robô só registra no log e segue.

## 4. Telemetria

- `POST /robot/telemetry` a cada 1 s, corpo `Telemetry` (`204` na resposta). Sem pose do AMCL ainda, o robô não envia.
- `route`: no máximo 50 pontos, tirados do `/plan` do Nav2 (vazia quando parado).
- `obstacles`: até 20 itens `{x, y, radius}`, em metros, no referencial `map` (um círculo por grupo de pontos do LiDAR). O robô leva o `/scan` para o `map` pela pose do AMCL, descarta o que coincide com o mapa estático (tolerância de 0,25 m), agrupa os pontos que estão a menos de 0,35 m um do outro e envia os grupos mais próximos do robô primeiro. Lista vazia quando não há nada novo à vista.
- `battery`: virtual (gasta andando, gasta pouco esperando, recarrega parado na base), de 0 a 100.
- `delivery_id`: a entrega em curso, `null` em `IDLE`.
- O backend ignora o `updated_at` do robô e grava a hora de recebimento.

## 5. Emergência

Há duas fontes de parada, e o robô as junta:

1. O tópico ROS `/geraldo/estop` (`std_msgs/Bool`), para quem está na máquina.
2. O backend: o painel chama `POST /robot/estop` com `{"active": true}` (papéis `admin` e `farmaceutico`) e o robô consulta `GET /robot/estop` (papel `robo`, resposta `{"active": bool}`). O backend começa com `active` falso. `GET /robot/estop` a cada 1 s, com o mesmo login do robô.

Regra de junção: com **qualquer** fonte ligada, o robô cancela a meta, para e o estado vira `PARADA_EMERGENCIA` (a telemetria acompanha, em até uns 2 s no caso do backend); só sai da parada com as duas fontes desligadas, e então volta ao estado anterior e refaz a mesma meta. Se a consulta ao backend falhar, vale o último valor conhecido: não libera nem aciona sozinho.

## 6. Resiliência

- Evento que não chega: 3 tentativas, 1 s entre elas; depois o robô segue sem ele (a carga está com ele).
- Consulta do status que falha conta como "ainda não" até o timeout.
- Backend fora do ar entre entregas ou no começo: o robô espera 5 s e tenta de novo. `uvicorn --reload` não derruba o robô.
- `401` em chamada autenticada: o robô faz login de novo uma vez e repete a chamada.
- Usuário ou senha errados no login (`401`/`403`) é erro fatal: o nó encerra dizendo o motivo.

## 7. O que cada frente precisa fazer

**Erik (backend)**
1. `GET /deliveries/{id}` precisa aceitar o papel `robo`. No plano da semana 1, só `admin`, `farmaceutico` e o solicitante veem a entrega; para o robô daria `404` e toda entrega terminaria em `FAILED` após 5 minutos. Já está no contrato (`openapi.yaml`, somente leitura).
2. Implementar `POST /robot/telemetry` (`204`; `403` para quem não é `robo`; `422` para corpo inválido) e repassar o último corpo no `GET /telemetry` e no WebSocket. WebSocket /ws/telemetry autentica por ?token=<JWT>, porque o navegador não manda cabeçalho; sem token válido o servidor fecha com 1008; clientes de linha de comando podem usar Authorization: Bearer.
3. `ARRIVED` leva a entrega a `AGUARDANDO_RECEBIMENTO`. `UNLOCKED` chega **depois** de `ENTREGUE`: aceitar, ou responder `409` (o robô tolera).
4. `POST /robot/next-task` deve pular `rotina` fora da janela de baixo pico: o robô não consegue devolver uma tarefa que o backend já marcou `EM_ROTA`.
5. Locais sem `waypoint` (a recepção) não podem ser origem nem destino: recusar na criação da entrega (já está no seu plano). Se uma passar, o robô manda `FAILED` e não se mexe.
6. `POST /robot/estop` (papéis `admin` e `farmaceutico`) guarda `{active}` em memória (começa em `false`) e `GET /robot/estop` (papel `robo`) devolve o último valor; `422` se o corpo não tiver `active` booleano.

**Vieira (web)**
1. Montar o MSW e as telas de estado do robô com `examples/robot-telemetry.json` (um corpo por estado) em vez de inventar fixtures.
2. "Confirmar recebimento" só faz sentido com `status = AGUARDANDO_RECEBIMENTO`; o estado do robô nessa hora é `AGUARDANDO_RETIRADA`.
3. `obstacles` traz até 20 círculos `{x, y, radius}` em metros no referencial `map` (pode vir vazio) e `route` também pode vir vazia.
4. Botão de emergência: `POST /robot/estop` com `{active: true}`; o estado `PARADA_EMERGENCIA` na telemetria confirma (em até uns 2 s). Para liberar, `{active: false}`: se o tópico ROS ainda estiver ligado, o robô continua parado.

**Pedro (qualidade)**
1. `tools/mock_robot.py` deve seguir a sequência da seção 2 e usar os corpos de `examples/robot-events.json`.
2. O teste de contrato precisa incluir a operação `POST /robot/telemetry` (nova no OpenAPI) na lista de pendentes até o Erik implementar.
3. O ataque "obstáculo falso na telemetria" mira `POST /robot/telemetry`; as mitigações são papel `robo`, estado no enum, bateria de 0 a 100 e `updated_at` ignorado.
4. `tools/mock_robot.py` também consulta `GET /robot/estop` a cada 1 s e fica em `PARADA_EMERGENCIA` enquanto vier `true`; o teste de contrato inclui `POST` e `GET /robot/estop`.
