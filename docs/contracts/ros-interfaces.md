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

Não há sensor a 180° (a traseira fica livre para o painel de manutenção).

`/scan` cobre cerca de 172° à frente: o baú bloqueia a traseira. A traseira é coberta pelos sensores `/range/rear_*` (semana 2).

## Ações e nós

- Navegação: ação `NavigateToPose` do Nav2 (`nav2_msgs/action/NavigateToPose`).
- `geraldo_dispatcher` (Samuel): chama `POST /robot/next-task`, converte `origin_waypoint` e `dest_waypoint` em poses usando `waypoints.yaml`, envia as metas ao Nav2 e reporta `POST /robot/events`.
- `waypoints.yaml`: `waypoints: { <id>: { room, x, y, yaw } }`, com `yaw` em graus.

## Estados (`/geraldo/state`)

`IDLE`, `CARREGANDO`, `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO`, `PARADA_EMERGENCIA`.
