# Prompt de partida — Samuel (robô, simulação, hospital, contratos)

Cole isto na sua IA no início da sessão:

```
Você é minha assistente de desenvolvimento no projeto G.E.R.A.L.D.O.
Leia, nesta ordem: AGENTS.md, robot/AGENTS.md, a spec em
docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md e os planos
docs/superpowers/plans/2026-11-05-semana1-samuel-fundacao.md e
docs/superpowers/plans/2026-11-05-semana1-samuel-robo.md.

Minha frente: robô e simulação (URDF, Gazebo, Nav2), hospital (hospital.yaml e geradores),
contratos e tokens do design system.

Tarefa: execute os planos tarefa por tarefa, na ordem do docs/superpowers/plans/README.md.
Não mude contratos já travados sem me avisar. Não toque em backend/, web/ nem security/.

Siga docs/padroes-de-projeto.md em todo código novo (SOLID, injeção pelo construtor,
Strategy/Factory no lugar de if/elif por tipo, funções puras); padrão só onde há variação real.

Antes de cada tarefa, diga o plano: o que vai fazer e quais arquivos vai tocar. Só então comece.
Pare no commit de cada tarefa e me mostre os testes passando.
```
