# Planos de implementação

Specs em [`../specs/`](../specs/). Cada plano é executado tarefa por tarefa, na ordem; cada tarefa termina com testes passando e um commit.

Os planos da semana 1 (fundação, backend, web e qualidade) cumpriram o papel e foram removidos; continuam no histórico do git. O que eles entregaram está descrito nos `AGENTS.md` de cada pasta.

| Plano | Entrega |
|---|---|
| [Hospital 3D](2026-11-12-hospital-3d.md) | Maquete do hospital em Blender, gerada de `robot/hospital/hospital_layout.json` |
| [Integração do robô](2026-11-13-integracao-robo.md) | Robô ligado ao backend, à web e ao robô de mentira |
| [Semana 2: dispatcher e sensores](2026-11-13-semana2-dispatcher-sensores.md) | Máquina de estados do dispatcher e sensores de alcance |
| [Semana 2: prioridades e emergência](2026-11-13-semana2-prioridades-emergencia.md) | Velocidade por prioridade e parada de emergência |
| [Semana 3, plano 1: contrato do robô](2026-11-13-semana3-1-contrato-robo.md) | Contrato do estop e ajuste de velocidade |
| [Semana 3, plano 1: medições](2026-11-13-semana3-1-medicoes.md) | Relatório de medições na simulação |
| [Semana 3, plano 2: backend](2026-11-13-semana3-2-backend.md) | Backend completo, robô de mentira e teste de contrato |
| [Semana 3, plano 3: web](2026-11-13-semana3-3-web.md) | Sistema web completo |
| [Semana 3, plano 4: app](2026-11-13-semana3-4-app.md) | App instalável (ponte ROS, orquestrador, Electron e visão 2D) |
| [Aba Farmácia](2026-11-15-farmacia-aprovacoes.md) | Aprovação e recusa de pedidos críticos |

**Regras de convivência**
- Branch por tarefa grande: `feat/<frente>-<assunto>`; PR para a `main`; nada direto na `main`.
- Contrato em `docs/contracts/` só muda por PR com aviso ao dono da frente afetada.
- Todo código segue [`docs/padroes-de-projeto.md`](../../padroes-de-projeto.md) (SOLID, injeção pelo construtor, Strategy/Factory no lugar de `if/elif` por tipo, funções puras).
