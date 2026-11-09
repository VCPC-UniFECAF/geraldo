#!/bin/bash
# Espera uma condição ficar verdadeira. Uso: wait_for.sh "<comando>" [segundos]
# Usado pelas tarefas do Cursor/VS Code: o Nav2 espera a simulação publicar o /scan e a varredura espera o Nav2 ativar.
cond="$1"
limit="${2:-120}"
SECONDS=0
while ((SECONDS < limit)); do
    if bash -c "$cond" > /dev/null 2>&1; then
        echo "pronto após ${SECONDS}s: $cond"
        exit 0
    fi
    sleep 2
done
echo "tempo esgotado (${limit}s) esperando: $cond" >&2
exit 1
