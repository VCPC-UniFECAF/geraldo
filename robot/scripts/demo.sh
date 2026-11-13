#!/usr/bin/env bash
# Sobe a demo inteira do G.E.R.A.L.D.O.: backend, web, simulação (Gazebo), Nav2 e dispatcher.
# Uso: bash robot/scripts/demo.sh [--headless]
#   --headless   sem a janela do Gazebo (só o servidor)
# Depois abra http://localhost:5173 e entre como medico1, farmaceutico1 ou admin (senha: GERALDO_DEMO_PASSWORD, padrão "demo").
# Cada execução começa com o banco e o estoque do seed. Ctrl+C derruba tudo.
# Antes, na primeira vez: backend/.venv com as dependências, npm install em web/ e colcon build em robot/ros2_ws.
# STACK_ROOT=<outro checkout> usa o backend e a web de lá (o robô continua vindo deste checkout).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STACK_ROOT="${STACK_ROOT:-$ROOT}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}" GZ_PARTITION="${GZ_PARTITION:-verif}"
HEADLESS=false
for arg in "$@"; do
  case "$arg" in
    --headless) HEADLESS=true ;;
    *) echo "uso: bash robot/scripts/demo.sh [--headless]" >&2; exit 2 ;;
  esac
done

for port in 8000 5173; do
  if ss -ltn | grep -qE ":$port\b"; then echo "A porta $port está ocupada: feche o que está nela e rode de novo." >&2; exit 1; fi
done
[ -x "$STACK_ROOT/backend/.venv/bin/uvicorn" ] || { echo "Falta o backend/.venv em $STACK_ROOT (veja backend/AGENTS.md)." >&2; exit 1; }
[ -d "$STACK_ROOT/web/node_modules" ] || { echo "Falta rodar npm install em $STACK_ROOT/web." >&2; exit 1; }

LOGS="${TMPDIR:-/tmp}/geraldo-demo"
mkdir -p "$LOGS"
rm -f "$LOGS/geraldo.db"
export GERALDO_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export GERALDO_DEMO_PASSWORD="${GERALDO_DEMO_PASSWORD:-demo}" GERALDO_ROBOT_PASSWORD="${GERALDO_ROBOT_PASSWORD:-robo-demo}"
export GERALDO_DATABASE_URL="sqlite:///$LOGS/geraldo.db" GERALDO_OFF_PEAK_HOURS="0-24"  # rotina liberada na demo
export GERALDO_API_URL="http://localhost:8000"
PIDS=()

# Cada processo roda na própria sessão (setsid), então o PID é também o grupo: kill -9 -- -PID derruba o processo
# e os filhos dele (o gz sim e o dispatcher só morrem com -9). Nunca se mata por nome: isso derruba o próprio shell.
start() {
  local name="$1"; shift
  setsid "$@" > "$LOGS/$name.log" 2>&1 &
  PIDS+=("$!")
  echo "iniciado: $name (log em $LOGS/$name.log)"
}

cleanup() {
  trap - EXIT INT TERM
  echo "derrubando a demo..."
  for pid in "${PIDS[@]}"; do
    kill -9 -- "-$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

wait_for() {  # wait_for "<descrição>" <segundos> <comando...>
  local what="$1" limit="$2"; shift 2
  SECONDS=0
  until "$@" > /dev/null 2>&1; do
    if ((SECONDS >= limit)); then echo "tempo esgotado esperando: $what (veja os logs em $LOGS)" >&2; exit 1; fi
    sleep 2
  done
  echo "pronto: $what (${SECONDS}s)"
}

start backend bash -c "cd '$STACK_ROOT/backend' && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000"
start web env VITE_API_URL="$GERALDO_API_URL" npm --prefix "$STACK_ROOT/web" run dev -- --port 5173 --strictPort
wait_for "backend" 30 curl -sf "$GERALDO_API_URL/health"

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [ ! -f "$ROOT/robot/ros2_ws/install/setup.bash" ]; then
  echo "Falta compilar o workspace: (cd robot/ros2_ws && colcon build --symlink-install) e rode de novo." >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$ROOT/robot/ros2_ws/install/setup.bash"
set -u

start simulacao ros2 launch geraldo_description sim.launch.py headless:="$HEADLESS"
wait_for "simulação publicando o /scan" 90 bash -c "ros2 topic list | grep -q '^/scan$'"
start nav2 ros2 launch geraldo_nav nav.launch.py
wait_for "Nav2 ativo" 120 bash -c "ros2 lifecycle get /bt_navigator | grep -q '^active'"
start dispatcher env PYTHONUNBUFFERED=1 ros2 run geraldo_dispatcher dispatcher

echo
echo "Demo no ar: http://localhost:5173 (medico1, farmaceutico1 ou admin; senha: $GERALDO_DEMO_PASSWORD)"
echo "Ctrl+C derruba tudo."
wait
