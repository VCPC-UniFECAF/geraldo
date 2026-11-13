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
| `/geraldo/estop` | `std_msgs/msg/Bool` | quem aciona → `geraldo_dispatcher` (`true` para, `false` libera); soma-se à consulta `GET /robot/estop` ao backend | 2 |
| `/amcl_pose` | `geometry_msgs/msg/PoseWithCovarianceStamped` | Nav2 (AMCL) → `geraldo_dispatcher` e `geraldo_bridge` | 3 |
| `/plan` | `nav_msgs/msg/Path` | Nav2 → `geraldo_dispatcher`, `curve_limiter` e `geraldo_bridge` | 3 |
| `/speed_limit` | `nav2_msgs/msg/SpeedLimit` | `curve_limiter` → Nav2 (limite absoluto em m/s; só esse nó publica) | 3 |

Não há sensor a 180° (a traseira fica livre para o painel de manutenção).

A câmera RGB-D fica na frente do robô e só publica as duas imagens acima (a ponte Gazebo → ROS as leva ao ROS). Nenhum nó lê marcador nelas.

`/scan` cobre cerca de 172° à frente: o baú bloqueia a traseira. A traseira é coberta pelos sensores `/range/rear_*` (semana 2).

## Ações e nós

- Navegação: ação `NavigateToPose` do Nav2 (`nav2_msgs/action/NavigateToPose`).
- `geraldo_dispatcher` (Samuel): chama `POST /robot/next-task`, converte `origin_waypoint` e `dest_waypoint` em poses usando `waypoints.yaml`, envia as metas ao Nav2 e reporta `POST /robot/events`.
- `geraldo_dispatcher` também lê o estado da parada de emergência do backend (`GET /robot/estop`, papel `robo`, a cada 1 s) e o junta com o tópico `/geraldo/estop`: com qualquer fonte ligada o robô para, e só sai da parada com as duas fontes desligadas (detalhes em `robot-protocol.md`).
- `curve_limiter` (Samuel): lê `/plan` e `/amcl_pose` e publica em `/speed_limit` a velocidade máxima que a curvatura à frente permite.
- `geraldo_bridge` (app, semana 3): publica/assina só `/geraldo/estop`, `/geraldo/state`, `/geraldo/battery`, `/amcl_pose`, `/plan`, `/scan` e `/range/*`. Nunca `/cmd_vel`.
- `waypoints.yaml`: `waypoints: { <id>: { room, x, y, yaw } }`, com `yaw` em graus.

## Estados (`/geraldo/state`)

`IDLE`, `CARREGANDO`, `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO`, `PARADA_EMERGENCIA`.

Significado dos estados na entrega: `CARREGANDO` é a espera na origem até a carga ser trancada (evento `LOADED`); `AGUARDANDO_RETIRADA` é a espera no destino até o solicitante confirmar o recebimento (o dispatcher consulta `GET /deliveries/{id}` até o status virar `ENTREGUE`) e termina no evento `UNLOCKED`. Com `/geraldo/estop` em `true`, o robô cancela a meta, para e publica `PARADA_EMERGENCIA`; em `false`, retoma o estado anterior.

`geraldo_dispatcher` também publica `/geraldo/state` e `/geraldo/battery` e envia o corpo de `Telemetry` a `POST /robot/telemetry` a cada 1 s. A bateria é virtual (a simulação não tem modelo de bateria).
