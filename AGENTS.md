# AGENTS.md — G.E.R.A.L.D.O.

Leia este arquivo inteiro antes de qualquer tarefa. Vale para qualquer IA ou pessoa que mexa neste repositório.

## O que é

G.E.R.A.L.D.O. é um robô hospitalar autônomo, **simulado no Gazebo**, que leva medicamentos e insumos da farmácia e do banco de sangue até consultórios, enfermarias, UTI, centro cirúrgico e pronto-socorro, e atualiza o estoque do hospital conforme transporta. Demo na ExpoTech, **sábado 28/11/2026**.

Fluxo de uma entrega:

```
Pedido no sistema web → Auth JWT → Command → Fila de prioridade → Reserva de estoque
 → Despacho ao robô → Nav2 navega e desvia → Chegada → Solicitante confirma o recebimento (libera a tampa)
 → Baixa/crédito de estoque → Telemetria em todo o caminho
```

Prioridades: `critica` (sangue, drogas de emergência; exige assinatura do farmacêutico), `media` (antibióticos, fluidos), `rotina` (lençóis, inventário obsoleto; só em baixo pico).

## Documentos que mandam

1. `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` — o que e por quê.
2. `docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md` — visual.
3. `docs/contracts/` — contratos (API, ROS, JWT).
4. `docs/superpowers/plans/` — o seu plano da semana, tarefa por tarefa.
5. `docs/padroes-de-projeto.md` — **como escrever o código** (SOLID, Factory, Strategy, Observer, Adapter, Builder, injeção de dependência).

## Mapa de pastas e donos

| Pasta | Dono | Conteúdo | Guia |
|---|---|---|---|
| `modelos-3d/` | Samuel | Modelo 3D | — |
| `hospital/`, `tools/` | Samuel | `hospital.yaml` e geradores | — |
| `ros2_ws/` | Samuel | Robô, simulação, Nav2, dispatcher | `ros2_ws/AGENTS.md` |
| `backend/` | Erik | API, estoque, fila, JWT | `backend/AGENTS.md` |
| `web/` | Vieira | Sistema web responsivo | `web/AGENTS.md` |
| `design-system/` | Samuel (tokens) e Vieira (componentes) | Tokens e guia visual | — |
| `security/`, `.github/`, `tools/mock_robot.py` | Pedro | Pentest, CI, robô de mentira | `security/AGENTS.md` |
| `unity/` | Samuel (extra) | Cockpit 3D | `unity/AGENTS.md` |
| `docs/contracts/` | Samuel | Contratos | — |

## Regras duras

1. **Contrato primeiro.** Não mude um contrato sozinho. Abra um PR em `docs/contracts/` e avise o dono da frente afetada.
2. **Estoque só por `Movimentacao`.** Nunca edite saldo direto; todo efeito vira um registro imutável.
3. **Todo código novo vem com teste.** Escreva o teste, veja falhar, implemente, veja passar.
4. **Nada na `main`.** Branch `feat/<frente>-<assunto>` e Pull Request.
5. **Nenhum segredo no repositório.** Senhas, chaves e tokens vêm de variáveis de ambiente. Seeds de demonstração usam valores de teste claramente falsos.
6. **Sem hex de cor solto.** Cores só pelos tokens de `design-system/` (regras no guia).
7. **Texto de interface em português**; comandos, pastas e código em inglês. Mensagem de erro diz o que houve e o que fazer.
8. **Na dúvida, pergunte antes de inventar.** Não crie contrato, endpoint, tópico ROS ou campo novo por conta própria.
9. **Ataques de teste só contra o ambiente local** (`localhost`). Nunca contra hosts externos.
10. **Padrões de projeto da disciplina.** Siga `docs/padroes-de-projeto.md`: uma responsabilidade por classe, dependências injetadas pelo construtor, Strategy ou Factory no lugar de `if/elif` por tipo, funções puras para transformar dados. Só use um padrão onde há variação real; sem padrão decorativo.

## Como rodar

| Área | Comando |
|---|---|
| Geradores e testes da raiz | `python -m pytest tools -q` |
| Backend | `cd backend && python -m pytest -q` e `uvicorn app.main:app --reload` |
| Web | `cd web && npm test -- --run` e `npm run dev` |
| Tokens do design system | `node design-system/tokens/build.mjs && (cd design-system && node --test)` |
| Simulação | `source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --symlink-install` (ver `ros2_ws/AGENTS.md`) |

## Definição de pronto (qualquer tarefa)

- Testes da área passando e nenhum teste de outra área quebrado.
- Commit pequeno, mensagem em português, no formato `tipo: o que mudou`.
- Contratos e documentação atualizados se a tarefa tocou algum deles.
- PR com descrição curta e o que foi testado (o template do GitHub traz o checklist de padrões).

## Como trabalhar com a IA

Antes de agir, **diga o plano**: o que vai fazer e quais arquivos vai tocar. Só depois comece. Faça uma tarefa do plano por vez e pare no commit.

## Quando travar

Falta algo de outra pessoa? Use o fixture ou a simulação indicada na própria tarefa e siga em frente; avise no grupo. Contrato errado ou ambíguo? Pare, abra PR em `docs/contracts/` e avise o Samuel.
