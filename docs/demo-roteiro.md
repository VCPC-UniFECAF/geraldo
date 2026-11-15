# Roteiro da demo (ExpoTech, sábado 28/11/2026)

Quem executa: Samuel. Máquina: a dele (Pop!_OS 24.04, ROS 2 Jazzy e Gazebo Harmonic nativos). Duração: uns 8 minutos.

## Antes de sair de casa (quinta 26 e sexta 27)

1. `bash robot/scripts/check_ros_env.sh` deve terminar em `AMBIENTE OK`.
2. `source /opt/ros/jazzy/setup.bash && (cd robot/ros2_ws && colcon build --symlink-install)`; `backend/.venv` criado e `npm install` feito em `web/` (o `demo.sh` avisa se faltar).
3. `python3 -m pytest tools robot -q` verde.
4. Varredura dos 10 pontos com a simulação e o Nav2 no ar (tarefa **GERALDO: varredura dos 10 pontos**): termina em `TODOS OS PONTOS OK`. O robô anda a 1,0 m/s no máximo (média 0,8 e rotina 0,5); se algum ponto falhar, não suba para a ExpoTech sem entender o motivo (ver `docs/superpowers/plans/2026-11-13-semana3-1-medicoes.md`).

## No palco

| # | O que fazer | O que a plateia vê |
|---|---|---|
| 1 | `bash robot/scripts/demo.sh` (sobe backend, web, Gazebo, Nav2 e dispatcher; `--fake-backend` troca backend e web pela API falsa, só para testar o robô). Espere `Demo no ar` e abra http://localhost:5173 | Gazebo com o hospital e o robô na base da farmácia |
| 2 | No sistema web, entre como `medico1` (senha `demo`) e peça uma entrega `critica` (banco de sangue para o centro cirúrgico); aprove como `farmaceutico1` (se o crítico for pedido por um farmacêutico, quem aprova é o outro: `farmaceutico1` e `farmaceutico2`, mesma senha) | A entrega entra na fila e o estoque reserva os itens |
| 3 | O robô sai sozinho: `A_CAMINHO`, `CARREGANDO`, `A_CAMINHO` | Anda a até 1,0 m/s (crítica) no corredor; o Painel mostra rota e estado |
| 4 | Com o robô no corredor norte: `bash robot/scripts/spawn_stretcher.sh on` | A maca aparece no corredor, o robô a vê (obstáculo no Painel) e replaneja pela cruz central |
| 5 | Botão **Parada de emergência** no Painel | Estado `PARADA_EMERGENCIA` em até uns 2 s e o robô para. Libere no Painel e ele retoma a mesma meta |
| 6 | `bash robot/scripts/spawn_stretcher.sh off` | Corredor livre |
| 7 | Chegada: `CHEGOU` e `AGUARDANDO_RETIRADA`. Em Minhas entregas, o solicitante confirma o recebimento | Tampa liberada (`UNLOCKED`), entrega `ENTREGUE` e o estoque do destino creditado |
| 8 | O robô volta à base (`VOLTANDO`, depois `IDLE`) | Baixa de estoque visível em Movimentações |

Se o robô parar sem motivo: veja `/tmp/geraldo-demo/*.log` (ou `$TMPDIR/geraldo-demo`). Se a emergência não liberar, confira o tópico: `ros2 topic pub -r 5 -t 3 /geraldo/estop std_msgs/msg/Bool "{data: false}"` (o tópico e o Painel precisam estar desligados).

## Depois

Ctrl+C no terminal do `demo.sh` derruba tudo (backend, web, simulação, Nav2 e dispatcher). Se algo ficar vivo: `kill -9 -- -PID` no PID que o `demo.sh` imprimiu; nunca `pkill`.
