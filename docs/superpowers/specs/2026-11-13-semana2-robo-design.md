# Semana 2 do robô (Samuel): dispatcher, sensores, prioridades e emergência — e escopo das semanas 3 e 4

**Data:** 13/11/2026 · **Dono:** Samuel · **Base:** spec do plano de desenvolvimento (05/11), seções 4.1, 8 e o quadro de semanas.
**M2:** qua 18/11 (pedido → reserva → robô entrega desviando obstáculo → estoque credita, visível no painel). **M3:** qua 25/11 (demo congelada). **ExpoTech:** sáb 28/11.

## 1. Estado de partida (verificado em 13/11)

Passando na `main` e na branch do hospital 3D: 91 testes, build, varredura dos 10 pontos (TODOS OS PONTOS OK) e desvio da maca (replaneja e chega). O `geraldo_dispatcher` tem 27 linhas úteis (`run_once`: origem, depois destino). O URDF só tem o LiDAR. Não há máquina de estados, eventos, telemetria, bateria, prioridade nem parada de emergência.

## 2. Decisões

| Tema | Decisão | Por quê |
|---|---|---|
| Telemetria | Novo `POST /robot/telemetry` (papel `robo`, corpo `Telemetry`, a cada 1 s) | O painel precisa de pose e rota ao vivo; mantém as frentes independentes (sem ROS no backend). É também o canal do ataque "obstáculo falso" do Pedro |
| Emergência | Tópico `/geraldo/estop` (`std_msgs/Bool`); botão no painel depois, via backend | Funciona já na demo por comando; o botão não muda o robô |
| `CARREGANDO` | Espera na origem até a carga ser trancada (evento `LOADED`) | Combina com o fluxo da entrega e com os eventos do contrato |
| Espera do recebimento | `AGUARDANDO_RETIRADA` consulta `GET /deliveries/{id}` até `ENTREGUE` | O contrato já tem o endpoint; nada novo |
| Bateria | Modelo virtual (a simulação não tem bateria) | Só alimenta `/geraldo/battery` e a telemetria |
| Câmera RGB-D | Semana 3, só se o M2 for atingido | Ordem de corte da spec (3º) |
| Docker, Unity | Fora do escopo das semanas 2 a 4 | Opcional e 1º corte; só voltam se o M2 for atingido sem atraso e o Samuel pedir |

Contratos já commitados em `docs/contratos-semana2` (`bf2460b`): `POST /robot/telemetry`, `/geraldo/estop`, significado dos estados. **Aviso ao Erik:** implementar `POST /robot/telemetry` e aceitar `UNLOCKED` depois de `ENTREGUE` (ver riscos).

## 3. Dispatcher com máquina de estados (subprojeto 1)

Uma responsabilidade por módulo, tudo injetado pelo construtor (`docs/padroes-de-projeto.md`):

- `states.py`: `State` (enum, os 7 estados do contrato), tabela de transições e `StateMachine` com listeners (**Observer**). Transição inválida levanta erro. Função pura, sem ROS.
- `ports.py`: `BackendPort` (`next_task`, `send_event`, `delivery_status`), `TelemetryPort` (`send_telemetry`) e `Navigator` (`go_to`, `cancel`). ISP: o dispatcher só vê o que usa.
- `dispatcher.py`: `Dispatcher.run_once()` conduz uma entrega:
  `IDLE → A_CAMINHO` (origem) `→ CARREGANDO` (`LOADED`) `→ A_CAMINHO` (destino) `→ CHEGOU` (`ARRIVED`) `→ AGUARDANDO_RETIRADA` (espera `ENTREGUE`, `UNLOCKED`) `→ VOLTANDO` (`base_robo`) `→ IDLE`.
  Falha de navegação, entrega cancelada ou espera estourada: evento `FAILED` com motivo, depois `VOLTANDO → IDLE`. Resultado devolvido: `ENTREGUE` ou `FALHOU` (com `failed_at`).
- `telemetry.py`: `build_telemetry(...)` (pura) e `BatteryModel` (pura: gasta andando, recarrega parado na base).
- `api.py`: `BackendClient` ganha `send_event`, `delivery_status` e `send_telemetry`; relogin uma vez em 401, como já faz.
- `node.py`: liga ao ROS: publica `/geraldo/state` (transient_local) e `/geraldo/battery`, lê a pose do AMCL e a rota do `/plan` e envia a telemetria a cada 1 s num executor próprio. O dispatcher continua no laço principal.
- `robot/scripts/fake_backend.py` ganha `POST /robot/events`, `GET /deliveries/{id}` (vira `ENTREGUE` depois de N consultas) e `POST /robot/telemetry`, para testar sem o Erik.

**Testes:** estados (transições válidas e inválidas), dispatcher com `FakeNavigator` e `ListBackend` (caminho feliz, falha de navegação, entrega cancelada, espera estourada), telemetria e bateria puras, `BackendClient` contra o `FakeBackend` HTTP. Sem Nav2 nem Gazebo.

## 4. Sensores (subprojeto 2)

5 sensores de alcance (`gpu_lidar` estreito, alcance 0,05 a 2,0 m) no URDF, nos tópicos do contrato: `/range/front_c` (0°), `/range/front_l45`, `/range/front_r45`, `/range/rear_l135`, `/range/rear_r135` (±45° e ±135°; nenhum a 180°). Ponte `ros_gz_bridge` para cada um, com teste de configuração e conferência na simulação (`ros2 topic echo --once`). O `/scan` não muda.

## 5. Prioridades e parada de emergência (subprojeto 3, ainda na semana 2)

- **Prioridade:** `Strategy` por prioridade escolhe o perfil de navegação (crítica: mais rápida e desvio mais agressivo; média: padrão; rotina: cede passagem e só roda em horário de baixo pico, janela configurável). A fila já vem ordenada pelo backend.
- **Emergência:** o dispatcher assina `/geraldo/estop`; `true` cancela a meta, zera o `/cmd_vel` e publica `PARADA_EMERGENCIA`; `false` retoma o estado anterior. Transições `qualquer estado → PARADA_EMERGENCIA → estado anterior` entram na máquina nesta etapa.

## 6. Escopo das semanas 3 e 4

| Quando | Escopo | Entrega |
|---|---|---|
| **Semana 3** (19 a 25/11) | Integração com o backend do Erik e o painel do Vieira (login, `next-task`, eventos, telemetria, confirmar recebimento); câmera RGB-D (se o M2 foi atingido); ajuste fino de velocidade e desvio; contrato e robô para o botão de emergência no painel; apoio ao ataque "obstáculo falso" do Pedro; cenários da demo; vídeo de reserva | **M3 qua 25/11:** demo congelada, só correção de bug depois |
| **Semana 4** (26 a 28/11) | Ensaio completo na máquina da demo (qui 26 e sex 27), sem funcionalidade nova; ExpoTech sáb 28 | Demo apresentada |

A spec original tem 3 semanas; "semana 4" é o período de 26 a 28/11 (ensaio e apresentação).

## 6.1 Riscos

- `UNLOCKED` depois de `ENTREGUE` pode dar 409 no backend do Erik: confirmar com ele; se der, o dispatcher envia `UNLOCKED` ao ver `AGUARDANDO_RECEBIMENTO` e não depois.
- Os 5 `gpu_lidar` extras pesam na simulação; a varredura dos 10 pontos precisa continuar passando e a carga de CPU será medida.
- Uma segunda sessão pode editar `feat/robo-hospital-3d`; este trabalho vive num worktree separado, em branches próprias.

## 7. Ordem e branches

1. `docs/contratos-semana2` (feito, PR de contrato com aviso ao Erik e ao Pedro).
2. `feat/robo-dispatcher-estados` (a partir da branch de contratos).
3. `feat/robo-sensores`.
4. `feat/robo-prioridades-estop`.
Um PR por branch, nada na `main`.
