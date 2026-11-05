# Planos de implementação — Semana 1 (05–11/11/2026)

Specs: [plano de desenvolvimento](../specs/2026-11-05-geraldo-plano-desenvolvimento-design.md) e [design system](../specs/2026-11-05-geraldo-design-system-design.md).

Cada pessoa executa **o seu plano**, tarefa por tarefa, na ordem. Cada tarefa termina com testes passando e um commit.

| Plano | Dono | Entrega ao final da semana 1 |
|---|---|---|
| [Fundação, contratos, hospital e tokens](2026-11-05-semana1-samuel-fundacao.md) | Samuel | Repo organizado, modelo 3D no repo, guia das IAs, contratos travados, hospital gerado de um YAML, tokens do design system |
| [Robô e simulação](2026-11-05-semana1-samuel-robo.md) | Samuel | Imagem Docker, URDF do robô, Gazebo com o hospital, `/cmd_vel` e `/scan`, Nav2 básico |
| [Backend](2026-11-05-semana1-erik-backend.md) | Erik | FastAPI com JWT, locais, estoque, criar entrega com reserva e fila de prioridade |
| [Web responsivo](2026-11-05-semana1-vieira-web.md) | Vieira | App web com tokens, componentes base e de domínio, tela de solicitar (mobile-first) sobre API simulada |
| [Qualidade e robô de mentira](2026-11-05-semana1-pedro-qualidade.md) | Pedro | CI no GitHub, teste de contrato da API, robô de mentira, coleção de requests |

## Ordem e dependências

```
Qui 05/11  Fundação T1 (repo + modelo 3D) e T2 (contratos)  ← destravam Erik, Vieira e Pedro
Sex 06/11  Fundação T3 (AGENTS.md + prompts) · Erik T1–T2 · Vieira T1 · Pedro T1 · Robô T1–T2
Sáb 07/11  Fundação T5 (tokens) ← destrava Vieira T2–T3 · Fundação T4 (hospital) · Erik T3 · Pedro T2
Dom 08/11  Contratos travados. Fundação T4 (hospital) e T6 (guia do design system) · Erik T4 · Vieira T4 · Pedro T3 · Robô T3–T4
Seg 09/11  Erik T5 · Vieira T5–T7 · Pedro T4 · Robô T4–T5
Ter 10/11  Integração das fatias; correções
Qua 11/11  M1: pedido na API vira meta no Nav2 e o robô anda no Gazebo
```

**Regras de convivência**
- Branch por tarefa grande: `feat/<frente>-<assunto>`; PR para a `main`; nada direto na `main`.
- Contrato em `docs/contracts/` só muda por PR com aviso ao dono da frente afetada.
- Quem destrava outra pessoa avisa no grupo no mesmo dia.
- Se uma tarefa bloquear por falta de algo de outra pessoa, use o fixture ou a simulação indicada na própria tarefa e siga em frente.
