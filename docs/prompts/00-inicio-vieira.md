# Prompt de partida — Vieira (sistema web)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, web/AGENTS.md, a spec do design system
docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md, docs/contracts/openapi.yaml
e o plano docs/superpowers/plans/2026-11-05-semana1-vieira-web.md.

Minha frente: sistema web responsivo (solicitar medicamento, acompanhar entregas, painel).

Tarefa: execute o plano tarefa por tarefa, começando pela Tarefa 1. Cada tarefa é TDD.
Use só cores e medidas dos tokens do design system (nada de hex solto). Mobile-first.
Enquanto o backend não estiver pronto, use os handlers MSW. Não mude docs/contracts/ sem PR
e aviso ao Samuel. Não toque em backend/, robot/ros2_ws/ nem security/.

Siga docs/padroes-de-projeto.md em todo código novo (SOLID, injeção pelo construtor,
Strategy/Factory no lugar de if/elif por tipo, funções puras); padrão só onde há variação real.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
