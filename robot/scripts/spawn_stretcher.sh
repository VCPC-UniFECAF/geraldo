#!/usr/bin/env bash
# Coloca (on, padrão) ou tira (off) a maca que bloqueia o corredor norte, com a simulação rodando.
# Uso (ROS carregado): bash robot/scripts/spawn_stretcher.sh [on|off]
set -euo pipefail
SHARE="$(ros2 pkg prefix geraldo_description)/share/geraldo_description"
case "${1:-on}" in
  on)  gz service -s /world/hospital/create --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean \
         --timeout 5000 --req "sdf_filename: \"$SHARE/worlds/maca.sdf\"" ;;
  off) gz service -s /world/hospital/remove --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean \
         --timeout 5000 --req 'name: "maca" type: MODEL' ;;
  *)   echo "uso: spawn_stretcher.sh [on|off]" >&2; exit 2 ;;
esac
