# Prompt de partida — Erik (backend)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, backend/AGENTS.md, docs/contracts/openapi.yaml,
docs/contracts/jwt.md e o plano docs/superpowers/plans/2026-11-05-semana1-erik-backend.md.

Minha frente: backend e gestão hospitalar (FastAPI, estoque, fila, JWT).

Tarefa: execute o plano tarefa por tarefa, começando pela Tarefa 1. Cada tarefa é TDD:
teste que falha, implementação mínima, teste que passa, commit.
Não mude docs/contracts/ sem PR e aviso ao Samuel. Não toque em web/, ros2_ws/ nem security/.
Estoque só muda por Movimentacao.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
