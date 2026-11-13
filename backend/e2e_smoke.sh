#!/usr/bin/env bash
# Teste de ponta a ponta com o servidor de verdade: sobe o uvicorn, roda o robô de mentira e confere
# pedido -> next-task -> eventos -> confirmar recebimento -> estoque (e assinatura dupla, emergência e WebSocket).
# Uso: bash backend/e2e_smoke.sh   (precisa de backend/.venv com as dependências e da porta 8000 livre)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API=http://127.0.0.1:8000
FAIL=0
expect() {  # expect "<esperado>" "<obtido>" "<descrição>"
  if [ "$1" = "$2" ]; then echo "ok: $3: $2"; else echo "FALHOU: $3: esperado '$1', veio '$2'"; FAIL=1; fi
}
if ss -ltn | grep -qE ':8000\b'; then echo "A porta 8000 está ocupada por outro processo: pare aqui e avise (não mate o que não é seu)."; exit 1; fi

WORK="$(mktemp -d)"
cd "$ROOT/backend" && . .venv/bin/activate
export GERALDO_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export GERALDO_DEMO_PASSWORD="demo-local-falsa" GERALDO_ROBOT_PASSWORD="robo-local-falso"
export GERALDO_DATABASE_URL="sqlite:///$WORK/e2e.db"

uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$WORK/uvicorn.log" 2>&1 &
UVICORN=$!
trap 'kill -9 $UVICORN 2>/dev/null' EXIT
for _ in $(seq 1 30); do curl -sf $API/health > /dev/null && break; sleep 0.5; done

token() { curl -s $API/auth/login -H 'content-type: application/json' -d "{\"username\":\"$1\",\"password\":\"$2\"}" | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'; }
field() { python -c "import sys,json; print(json.load(sys.stdin)$1)"; }
MED=$(token medico1 "$GERALDO_DEMO_PASSWORD"); PHARM=$(token farmaceutico1 "$GERALDO_DEMO_PASSWORD"); ROBO=$(token robo "$GERALDO_ROBOT_PASSWORD")
auth() { echo "authorization: Bearer $1"; }
JSON='content-type: application/json'

echo "--- 1. pedido (media): farmacia -> consultorio1"
expect NA_FILA "$(curl -s $API/deliveries -H "$(auth $MED)" -H "$JSON" -d '{"origin_id":"farmacia","items":[{"item_id":"dipirona-500mg","quantity":5}],"priority":"media"}' | field '["status"]')" "status do pedido"

echo "--- 2. robô de mentira: next-task, telemetria, LOADED, ARRIVED, espera, UNLOCKED"
python "$ROOT/tools/mock_robot.py" --api $API --travel 1 --poll 1 --report --once > "$WORK/robot.log" 2>&1 &
ROBOT=$!
STATUS=""
for _ in $(seq 1 30); do
  STATUS=$(curl -s $API/deliveries/1 -H "$(auth $MED)" | field '["status"]')
  [ "$STATUS" = AGUARDANDO_RECEBIMENTO ] && break; sleep 1
done
expect AGUARDANDO_RECEBIMENTO "$STATUS" "o robô chegou e espera a confirmação"

echo "--- 3. o solicitante confirma o recebimento"
expect ENTREGUE "$(curl -s -X POST $API/deliveries/1/confirm-receipt -H "$(auth $MED)" | field '["status"]')" "status depois de confirmar"
wait $ROBOT; expect 0 "$?" "código de saída do robô"
expect "entrega 1: farmacia_balcao -> cons1_entrega" "$(cat "$WORK/robot.log")" "log do robô"

echo "--- 4. estoque da dipirona e movimentações"
STOCK=$(curl -s $API/stock -H "$(auth $MED)" | python -c 'import sys,json; [print(s["location_id"], s["quantity"], s["reserved"]) for s in json.load(sys.stdin) if s["item_id"]=="dipirona-500mg"]')
expect "consultorio1 5 0
farmacia 415 0" "$STOCK" "saldo e reservado (local saldo reservado)"
MOVES=$(curl -s "$API/movements?delivery_id=1" -H "$(auth $MED)" | python -c 'import sys,json; [print(m["type"], m["location_id"], m["quantity"]) for m in json.load(sys.stdin)]')
expect "RESERVA farmacia 5
BAIXA farmacia 5
CREDITO consultorio1 5" "$MOVES" "movimentações da entrega 1"

echo "--- 5. última telemetria do robô"
expect IDLE "$(curl -s $API/telemetry -H "$(auth $MED)" | field '["robot_state"]')" "robot_state"

echo "--- 6. assinatura dupla: a crítica só sai da fila depois da aprovação do farmacêutico"
expect PENDENTE_APROVACAO "$(curl -s $API/deliveries -H "$(auth $MED)" -H "$JSON" -d '{"origin_id":"banco_sangue","items":[{"item_id":"bolsa-sangue-o-neg","quantity":1}],"priority":"critica"}' | field '["status"]')" "status da crítica"
expect 204 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/robot/next-task -H "$(auth $ROBO)")" "next-task antes da aprovação"
expect NA_FILA "$(curl -s -X POST $API/deliveries/2/approve -H "$(auth $PHARM)" | field '["status"]')" "status depois da aprovação"
expect "2 EM_ROTA banco_sangue_retirada cons1_entrega" "$(curl -s -X POST $API/robot/next-task -H "$(auth $ROBO)" | python -c 'import sys,json; d=json.load(sys.stdin); print(d["id"], d["status"], d["origin_waypoint"], d["dest_waypoint"])')" "tarefa entregue ao robô"

echo "--- 7. emergência pelo painel"
expect 204 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/robot/estop -H "$(auth $PHARM)" -H "$JSON" -d '{"active":true}')" "ligar a emergência"
expect True "$(curl -s $API/robot/estop -H "$(auth $ROBO)" | field '["active"]')" "o robô lê active"
expect 204 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/robot/estop -H "$(auth $PHARM)" -H "$JSON" -d '{"active":false}')" "desligar a emergência"

echo "--- 8. WebSocket"
expect IDLE "$(python - "$MED" <<'PY'
import asyncio, json, sys, websockets

async def main():
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/telemetry?token={sys.argv[1]}") as ws:
        print(json.loads(await asyncio.wait_for(ws.recv(), 3))["robot_state"])

asyncio.run(main())
PY
)" "primeiro quadro do WebSocket"

expect 0 "$(grep -c "$MED" "$WORK/uvicorn.log")" "o token do WebSocket não aparece no log do servidor"

echo "--- 9. trilha de auditoria no log do servidor"
grep -E "geraldo\." "$WORK/uvicorn.log"
expect 1 "$(grep -c 'entrega 1: AGUARDANDO_RECEBIMENTO -> ENTREGUE (por medico1)' "$WORK/uvicorn.log")" "auditoria do recebimento"

[ $FAIL -eq 0 ] && echo "E2E OK" || echo "E2E COM FALHAS"
exit $FAIL
