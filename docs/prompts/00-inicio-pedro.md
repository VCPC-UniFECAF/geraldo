# Prompt de partida — Pedro (qualidade e segurança)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, security/AGENTS.md, docs/contracts/openapi.yaml
e o plano docs/superpowers/plans/2026-11-05-semana1-pedro-qualidade.md.

Minha frente: qualidade e segurança (CI, teste de contrato, robô de mentira e, na semana 3, pentest).

Tarefa: execute o plano tarefa por tarefa, começando pela Tarefa 1. Cada tarefa é TDD quando há código.
Ataques de teste só contra localhost. Não mude docs/contracts/ sem PR e aviso ao Samuel.
Não implemente funcionalidades do backend, da web nem do robô: a sua frente é testá-las.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
