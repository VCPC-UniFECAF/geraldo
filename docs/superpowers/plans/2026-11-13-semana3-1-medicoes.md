# Medições na simulação (semana 3, plano 1)

Data: 14/11/2026 · Branch: `feat/semana3-plano1` · Commit das medições: efae8d7 · Script: `robot/scripts/measure_speed.py` · Simulação: hospital 3D, `headless:=true`, `ROS_DOMAIN_ID=77`, `GZ_PARTITION=verif`, pilha reiniciada do zero a cada corrida (robô na base).

Configuração do Nav2: a da `main` (`nav2_params.yaml` e `make_nav2_params.py` idênticos): `CRUISE_SPEED` 1,0 m/s, janela do costmap local de 3 m, MPPI padrão. Perfis por prioridade 1,0 / 0,8 / 0,5 m/s (decisão do Samuel em 14/11: manter a velocidade que estava antes dos 3 m/s). A branch acrescenta câmera RGB-D, estop do backend e este script; não mexe na navegação.

## Velocidade real de cruzeiro: ~0,55 m/s (já era assim na `main`; resolvido em 15/11, ver "Cruzeiro (15/11)")

Com o teto em 1,0 m/s o robô não passa de uns 0,55 m/s no corredor reto. Conferido nas duas pontas, base até (42, 29) sem dispatcher:

| Árvore | Resultado |
|---|---|
| `main` (worktree de integração, sem câmera) | chegou em 82 s, pico 0,54 m/s |
| esta branch (com câmera) | pico 0,54 e 0,53 m/s nas duas corridas de freio da 1ª rodada |

Os arquivos do Nav2 são iguais, então a causa é da `main`: a janela de 3 m do costmap local é menor que o horizonte do MPPI (56 passos × 0,05 s) a 1,0 m/s, e o controlador fica em torno de 0,5 m/s. Os perfis `critica` (1,0), `media` (0,8) e `rotina` (0,5) só diferenciam de fato a `rotina`. Não é regressão desta branch; fica registrado.

## Frenagem e curva de 90° a 1,0 m/s (teto)

| Cenário | Linha `RESULTADO` | Segurança (critério da Task 9) |
|---|---|---|
| freio, 1ª rodada (limiar 0,9 m/s) | `nao_atingiu_1.0_m_s pico=0.54 m/s fim_da_meta=SUCCEEDED` (2 corridas, picos 0,54 e 0,53) | não aplicável: o robô nunca chega a 0,9 m/s |
| freio (1ª, limiar 0,5 m/s) | `v_no_comando=0.50 m/s distancia_ate_parar=0.07 m tempo_ate_parar=0.24 s` | seguro (≤ 2,0 m) |
| freio (2ª) | `v_no_comando=0.51 m/s distancia_ate_parar=0.07 m tempo_ate_parar=0.24 s` | seguro |
| freio (3ª) | `v_no_comando=0.50 m/s distancia_ate_parar=0.07 m tempo_ate_parar=0.24 s` | seguro |
| curva de 90° (1ª) | `chegou=True v_max=0.57 m/s aceleracao_lateral_max=0.17 m/s2 velocidade_na_porta=0.51 m/s menor_leitura_do_lidar=0.44 m` | segura (chegou, lidar ≥ 0,30 m) |
| curva de 90° (2ª) | `chegou=True v_max=0.56 m/s aceleracao_lateral_max=0.17 m/s2 velocidade_na_porta=0.52 m/s menor_leitura_do_lidar=0.43 m` | segura |

Leitura: a 0,5 m/s o robô para em 7 cm e 0,24 s depois do cancelamento da meta, bem abaixo do alcance de 2 m dos sensores `/range/*`. A curva de 90° na porta do centro cirúrgico é feita a 0,51 a 0,52 m/s, com aceleração lateral de 0,17 m/s² e pelo menos 0,43 m de folga até o obstáculo mais próximo visto pelo LiDAR (a porta tem 1 m e o robô, 0,5 m). A maca não foi medida nesta rodada (o pedido foi frenagem e curva); os obstáculos reais na telemetria ficaram provados na PR #19 (0 falsos positivos em 581 scans a 4 m).

## Parada de emergência do painel, no Gazebo (Task 6)

Backend real + dispatcher + pilha da branch. `medico1` pediu farmácia → consultório 2 (prioridade média); `farmaceutico1` acionou o painel (`POST /robot/estop`).

| Passo | Medido |
|---|---|
| robô andando antes do acionamento | estado `A_CAMINHO`, 0,42 m/s |
| `{"active": true}` → `PARADA_EMERGENCIA` na telemetria | 2,0 s (consulta a cada 1 s + telemetria a cada 1 s) |
| velocidade abaixo de 0,05 m/s | 1,6 s |
| parado por 10 s | v = 0,000 m/s e deslocamento 0,00 m, estado `PARADA_EMERGENCIA` |
| `{"active": false}` → `A_CAMINHO` | 1,0 s; v > 0,2 m/s em 1,3 s |
| depois | mesma meta concluída: `AGUARDANDO_RETIRADA`, confirmação, entrega `ENTREGUE`, robô `IDLE` na base, movimentações RESERVA, BAIXA e CREDITO |

A regra "só sai da parada com as duas fontes desligadas" está coberta pelos testes do dispatcher (`test_the_robot_leaves_the_emergency_only_when_both_sources_are_off`); no Gazebo só o painel foi exercitado.

## Varredura dos 10 pontos (Task 10)

Comando: `python3 robot/scripts/nav_goal_sweep.py` com a pilha da branch (câmera incluída, 1,0 m/s). Saída:

```
ok     farmacia_balcao              5s
ok     banco_sangue_retirada       53s
ok     rouparia_coleta             77s
ok     cc_entrega                  58s
ok     uti_entrega                 45s
ok     ps_entrega                  94s
ok     cons1_entrega               86s
ok     cons2_entrega               33s
ok     enf214_entrega              58s
ok     enf215_entrega              44s
TODOS OS PONTOS OK
```

Tentativas: 1. Duração total: 553 s (9 min 13 s).

## Tentativa a 3 m/s (14/11, abandonada por decisão do Samuel)

Tentou-se um robô a 3,0 m/s para qualquer prioridade: `CRUISE_SPEED` 3,0, janela do costmap local de 18 m, `vx_std` 0,5, `prune_distance` 9,0, `PathFollowCritic` (offset 60, peso 15) e `PathAlignCritic` (offset 100, depois 50), mais um nó `curve_limiter` pelo `/speed_limit`. Em linha reta o robô chegou a 3,00 m/s, mas **não saía da farmácia de forma confiável**: dava ré rumo à porta de 1 m (partia virado para o sul) e ficava preso no batente ("Failed to make progress", "Optimizer fail to compute path").

Corridas partindo da base até (42, 29), pilha nova a cada uma:

| Configuração (PathFollow offset / PathAlign offset) | Resultado |
|---|---|
| 60 / 100 (as do plano) | falhou 3 de 3 (freio: picos 1,43, 1,44 e 0,27 m/s, meta `FAILED`; curva de 90°: `chegou=False`, v_max 1,46 m/s) |
| 30 / 50 | chegou em 143 s, pico 0,37 m/s |
| 30 / 100 | falhou (34 s, pico 0,24 m/s) |
| 60 / 50, 5 corridas | chegou em 45 s (pico 3,00), 150 s (1,77), 165 s (2,42); falhou em 96 s (2,12) e 36 s (0,24): 3 de 5 |
| 60 / 40 | falhou nas duas metas (picos 0,25 e 0,15 m/s) |
| 45 / 50 | falhou em `cc_entrega` (pico 0,24); voltou à base em 18 s |
| 60 / 50, `cc_entrega` e volta à base | chegou em 43 s (pico 3,00); a volta falhou (163 s, preso na porta norte do CC) |

O resultado era aleatório e não variava de forma regular com os parâmetros: o problema é sair e entrar pelas portas de 1 m. Fora do protocolo, uma frenagem a 2,89 m/s parou em 2,04 m (acima do alcance de 2 m dos sensores). O `curve_limiter` foi removido na volta a 1,0 m/s: com teto de 1,0 m/s, `a_brake` de 1,5 m/s² e ponto a cada 0,5 m, o menor limite possível (√(0,3² + 2·1,5·0,5) = 1,26 m/s) fica acima do teto e ele nunca age. Voltar a 3 m/s exigiria resolver a saída pelas portas (por exemplo, proibir a ré no MPPI ou girar no lugar antes de sair) e trazer o `curve_limiter` de volta (commit cbe7fc7 no histórico da branch).

## Cruzeiro (15/11): de ~0,54 para 1,0 m/s só com parâmetros do MPPI

Causa do cruzeiro de ~0,54 m/s (investigação em `exp/cruzeiro`, 81 trechos, pilha reiniciada a cada variante): **três limites dentro do MPPI**, cada um aparece quando o anterior é removido.

| Limite | Conta | Teto | Medido |
|---|---|---|---|
| Janela do costmap local (3 m, raio 1,5 m) contra o horizonte 56 × 0,05 = 2,8 s | 1,5 / 2,8 | 0,536 m/s | 0,54 (`main`) |
| `prune_distance` 1,7 m | 1,7 / 2,8 | 0,607 m/s | 0,60 (janela 5 ou 7 m) |
| `vx_std` 0,2, com os dois acima abertos | — | ~0,67 m/s | 0,67 (janela 7 + prune 4,0 ou 28 passos) |

Com janela 7 m, `prune` 4,0 e `vx_std` 0,4 o robô chegou a 1,00 m/s; com janela 5 m o teto passou a 0,89 (2,5 / 2,8), como previsto. Não são os críticos de caminho, o suavizador nem a CPU: com o teto em 0,67 m/s o `/cmd_vel_nav` (saída do controlador) já parava em 0,67 e a taxa ficou em 20 Hz em todas as corridas. A mudança mínima, que não mexe na janela nem no `prune`: **`time_steps` 56 → 28** (horizonte de 1,4 s: tetos de 1,07 e 1,2 m/s) e **`vx_std` 0,2 → 0,4** (`MPPI_TUNING` em `robot/scripts/make_nav2_params.py`). Os perfis de 1,0/0,8/0,5 m/s do `robot-protocol.md` passam a valer de verdade; o contrato não muda.

Candidatas validadas (C2: `time_steps` 28; C3: `time_steps` 36; as duas com `vx_std` 0,4):

| | `main` | C2 (28 passos) | C3 (36 passos) |
|---|---|---|---|
| Pico crítica / média / rotina | 0,54 / 0,54 / 0,50 | **1,00 / 0,80 / 0,50** | 0,86 a 0,89 (a conta da janela dá 1,5 / 1,8 = 0,83) |
| Base → (42, 29), crítica | 81 s | 45 s | não medido |
| Maca surge a 8 m no corredor, meta (42, 29): corridas | 4 | **10** | **10** |
| Chegaram | 2 (as outras 2 não contornaram em 241 s) | 10 de 10 | 10 de 10 |
| Encostaram (< 0,35 m) | 0 | **0** | **0** |
| Distância mínima à maca (mín / média / máx) | 0,58 a 5,56 m | 0,45 / 0,59 / 0,84 m | 0,51 / 0,61 / 0,91 m |
| Tempo até (42, 29) com a maca | 132 s (nas 2 que chegaram) | 148 a 159 s (média 152 s) | 172 a 193 s (média 183 s) |
| Frenagem (cancelar a meta a ~1,0 m/s) | de 0,52 m/s: 0,09 m e 0,27 s | de 0,98 m/s: 0,24 m e 0,44 s; de 0,97: 0,25 m e 0,48 s | não medido |
| Varredura dos 10 pontos | `TODOS OS PONTOS OK`, 553 s | `TODOS OS PONTOS OK`, 322 s | não medida |
| Portas de 1 m (farmácia: 12 trechos; centro cirúrgico: 2 idas e 2 voltas) | todas passaram | todas passaram | — |
| Controlador / CPU do container do Nav2 | 20 Hz / 94 a 103 % | 20 Hz / 88 a 93 % | — |

Escolha: as duas passaram na maca (0 encostões em 10), então ficou a mais rápida, **C2**. Na primeira triagem, com 4 corridas, a C2 tinha encostado uma vez (0,33 m); nas 10 corridas de validação não repetiu (mínimo 0,45 m), então a margem é estreita: se o horizonte de 1,4 s preocupar, a C3 é o meio-termo (mais lenta, 0,88 m/s). Varredura da C2:

```
ok     farmacia_balcao              4s
ok     banco_sangue_retirada       35s
ok     rouparia_coleta             43s
ok     cc_entrega                  31s
ok     uti_entrega                 26s
ok     ps_entrega                  54s
ok     cons1_entrega               49s
ok     cons2_entrega               20s
ok     enf214_entrega              34s
ok     enf215_entrega              26s
TODOS OS PONTOS OK
```

Ressalvas: o container do Nav2 roda perto de um núcleo inteiro (qualquer variante); a taxa real da simulação (RTF) não foi medida; a maca foi medida só a 8 m no corredor nesta validação.

## Proposta

Nenhum cenário medido a 1,0 m/s reprovou. O cruzeiro de ~0,55 m/s foi resolvido em 15/11 com `time_steps` 28 e `vx_std` 0,4 (seção acima).
