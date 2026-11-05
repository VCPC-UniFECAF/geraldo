# G.E.R.A.L.D.O. — Design system (spec de design)

**Data:** 05/11/2026 · **Dono:** Samuel (tokens e documento) · **Implementação dos componentes:** Vieira · **Status:** direção visual aprovada pelo líder; spec para revisão

Subprojeto da [spec do plano de desenvolvimento](2026-11-05-geraldo-plano-desenvolvimento-design.md) (seção 10).
Estrutura baseada no `DESIGN_SYSTEM.md` do barberschedule (marca, regras de ouro, paleta, tipografia, espaçamento, formas, elevação, motion, acessibilidade, ícones, componentes base e de domínio), adaptada para **web responsivo** (computador e navegador do celular) e para o cockpit Unity.

---

## 0. Escopo e entregas

| Entrega | O que é | Quem | Quando |
|---|---|---|---|
| `design-system/tokens/tokens.json` | Fonte única de todos os tokens | Samuel | sáb 07/11 (v0) |
| `design-system/tokens/build.mjs` | Gera `dist/tokens.css`, `dist/tailwind.preset.cjs` e `dist/GeraldoTokens.cs` | Samuel | sáb 07/11 |
| `design-system/DESIGN_SYSTEM.md` | Documento de referência para pessoas e IAs (este conteúdo, em formato de guia) | Samuel | dom 08/11 |
| Componentes base e de domínio no app web | Implementação com os tokens | Vieira | semanas 1–2 |
| `design-system/showcase/` | Página com todos os componentes e estados (GitHub Pages) | Vieira | semana 2 |
| `design-system/tests/` | Teste de contraste e teste "sem hex solto" | Pedro | semana 2 |

**Fora do escopo da v1:** modo escuro, app nativo, biblioteca publicada em npm, Storybook.

**Decisão em aberto (dono: Vieira, até 07/11):** stack do app web. Recomendação: React + Vite + TypeScript + Tailwind v3 (o preset gerado já vem pronto). Se for outra, os tokens continuam valendo como CSS variables.

## 1. Direção de marca

Clínica, limpa e confiável. Base branca, azul e vermelha:
- **Azul** é a ação e a identidade (botões, item ativo, números de destaque).
- **Vermelho** é alerta clínico: só para o que exige atenção imediata.
- Cards brancos de cantos grandes sobre um fundo azul-acinzentado muito claro; hierarquia por tamanho e peso, não por cor.
- Inspiração visual: dois dashboards hospitalares fornecidos pelo líder (cards em linhas arredondadas, cartão de destaque em azul sólido, listas com horário à esquerda e selo à direita, banner de aviso de largura total, barra lateral estreita de ícones). Sem chat nem prontuário de paciente.

## 2. Regras de ouro (valem para pessoas e para IAs)

1. **Sem hex solto.** Cor sempre via token (`var(--azul-500)` ou classe do preset). Exceção: SVG/canvas, importando de `tokens.css` ou do JS gerado.
2. **Vermelho só para:** prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro. Nunca para decoração nem para ação primária.
3. **Um botão primário por tela ou seção.** Os demais são secundário ou fantasma.
4. **Status nunca só por cor.** Sempre cor + ícone ou texto.
5. **Números com `tabular-nums`** (saldo, quantidade, horário, bateria, contagens).
6. **Mobile-first.** Escreva o layout do celular primeiro e amplie com os breakpoints.
7. **Alvo de toque mínimo de 44 × 44 px** em controles.
8. **Texto da interface em português**, em *sentence case*, botão com verbo curto ("Solicitar medicamento"), sem "por favor", sem ponto final em rótulos e títulos. Mensagem de erro diz o que houve e o que fazer.
9. **Nada de valores soltos de espaçamento:** só a escala do §5.

## 3. Cores

### 3.1 Azul (primária)

| Token | Hex | Uso |
|---|---|---|
| `azul-50` | `#EEF3FF` | Fundo de item ativo, hover suave |
| `azul-100` | `#DCE6FF` | Fundo de selo "média", chips |
| `azul-200` | `#B9CCFF` | Bordas de foco suave |
| `azul-300` | `#8FAEFF` | Decoração |
| `azul-400` | `#5C86F5` | Anel de foco, gráficos |
| **`azul-500`** | **`#3A66E8`** | **Primária: botões, item ativo, barras, StatCard** |
| `azul-600` | `#2B52C9` | Hover/pressed; texto de link sobre claro |
| `azul-700` | `#223F9C` | Texto sobre `azul-100` |
| `azul-800` | `#1A3074` | Ênfase alta |
| `azul-900` | `#12214F` | Base de sombra e títulos escuros |

### 3.2 Vermelho (alerta clínico)

| Token | Hex | Uso |
|---|---|---|
| `vermelho-50` | `#FEF1F1` | Fundo de banner de alerta |
| `vermelho-100` | `#FDDCDC` | Fundo de selo "crítica" |
| `vermelho-200` | `#F9B4B8` | Borda de banner |
| `vermelho-300` | `#F38A91` | Decoração |
| `vermelho-400` | `#EB5963` | Hover |
| **`vermelho-500`** | **`#D92D3A`** | **Crítica, perigo, estoque abaixo do mínimo, botão destrutivo** |
| `vermelho-600` | `#B91C2B` | Texto de alerta sobre claro |
| `vermelho-700` | `#8C1522` | Texto sobre `vermelho-100` |
| `vermelho-800` | `#650F18` | Ênfase |
| `vermelho-900` | `#42090F` | Ênfase máxima |

### 3.3 Neutros (cinza-azulado)

| Token | Hex | Uso |
|---|---|---|
| `branco` | `#FFFFFF` | Cards, campos |
| `fundo` | `#F4F6FB` | Fundo das telas |
| `neutro-50` | `#EEF1F7` | Linhas de lista, selo "rotina" |
| `neutro-100` | `#E5E9F2` | Bordas e divisórias |
| `neutro-200` | `#D3D9E6` | Bordas de campo em repouso |
| `neutro-300` | `#B6BED0` | Ícones inativos, desabilitado |
| `neutro-400` | `#8F98AD` | Placeholder |
| `neutro-500` | `#636B7E` | Texto de apoio |
| `neutro-600` | `#4A5266` | Texto secundário forte |
| `neutro-700` | `#323A4D` | Rótulos |
| **`tinta`** (`neutro-800`) | **`#1B2233`** | **Texto principal** |
| `neutro-900` | `#0F1422` | Contraste máximo |

### 3.4 Feedback (fora da identidade)

| Token | Hex | Uso |
|---|---|---|
| `sucesso-50` / `sucesso-500` / `sucesso-700` | `#E8F6EE` / `#1F9D61` / `#146B41` | Entregue, confirmado |
| `aviso-50` / `aviso-500` / `aviso-700` | `#FEF5E3` / `#E39A1B` / `#8A5A07` | Atenção, estoque próximo do mínimo, aguardando aprovação |

### 3.5 Semântica de domínio

**Prioridade** (nunca usa âmbar; crítica e erro não se confundem com "média"):

| Valor | Fundo | Texto | Ponto |
|---|---|---|---|
| `critica` | `vermelho-100` | `vermelho-700` | `vermelho-500` |
| `media` | `azul-100` | `azul-700` | `azul-500` |
| `rotina` | `neutro-50` | `neutro-600` | `neutro-400` |

**Status da entrega:**

| Estado | Cor | Ícone (Lucide) |
|---|---|---|
| `PENDENTE_APROVACAO` | aviso | `ShieldCheck` |
| `NA_FILA` | neutro | `Clock` |
| `EM_ROTA` | azul | `Bot` |
| `AGUARDANDO_RECEBIMENTO` | azul (destaque) | `PackageCheck` |
| `ENTREGUE` | sucesso | `CircleCheck` |
| `CANCELADA` | neutro, texto riscado | `Ban` |
| `FALHOU` | vermelho | `TriangleAlert` |

**Estado do robô:** `IDLE`, `CARREGANDO` → neutro; `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO` → azul; `PARADA_EMERGENCIA` → vermelho.

**Nível de estoque:** acima de 120% do mínimo → azul; entre 100% e 120% → aviso; abaixo do mínimo → vermelho, com o texto "Abaixo do mínimo".

### 3.6 Contraste

Pares texto/fundo usados nos componentes precisam de **pelo menos 4,5:1** (texto normal) ou 3:1 (texto grande e ícones). Referência: `branco` sobre `azul-500` e sobre `vermelho-500` ficam perto de 4,9:1 e 4,8:1; `neutro-500` sobre `fundo` passa de 4,5:1. O teste em `design-system/tests/` calcula todos os pares usados e falha o CI se algum ficar abaixo.

## 4. Tipografia

- **Plus Jakarta Sans** (display): títulos de tela, nome do robô, números grandes dos `StatCard`.
- **Inter** (corpo): parágrafos, rótulos, campos, tabelas.
- Fontes carregadas pelo Google Fonts (pesos 400, 500, 600, 700); fallback `system-ui, sans-serif`.

| Token | Tamanho / linha | Uso |
|---|---|---|
| `texto-xs` | 12 / 16 | Metadados, horário em lista |
| `texto-sm` | 14 / 20 | Rótulos, texto de tabela, selos |
| `texto-base` | 16 / 24 | Corpo, campos |
| `texto-lg` | 18 / 28 | Título de card |
| `texto-xl` | 20 / 28 | Título de seção |
| `texto-2xl` | 24 / 32 | Título de tela |
| `texto-3xl` | 30 / 36 | Saudação do painel |
| `texto-4xl` | 36 / 44 | Número de destaque (`StatCard`) |

Pesos: 400 corpo, 500 rótulos, 600 botões e títulos de card, 700 números de destaque. Números sempre com `font-variant-numeric: tabular-nums`.

## 5. Espaçamento e layout

Base de 4 px (escala padrão do Tailwind: 1 = 4, 2 = 8, 3 = 12, 4 = 16, 5 = 20, 6 = 24, 8 = 32).

| Token | Valor | Uso |
|---|---|---|
| `gutter-tela` | 16 (celular), 24 (≥ 768) | Padding lateral das telas |
| `gap-cards` | 12 (celular), 16 (≥ 768) | Espaço entre cards |
| `altura-controle` | 44 | Botões e campos (também o alvo de toque) |
| `largura-sidebar` | 72 | Barra lateral de ícones (≥ 768) |
| `largura-max` | 1280 | Largura máxima do conteúdo |

**Breakpoints:** `sm` 640, `md` 768, `lg` 1024, `xl` 1280.
**Navegação:** abaixo de 768 px a barra lateral vira **barra inferior** com 4 itens; a partir de 768 px é a barra lateral de ícones com indicador de item ativo (barra azul à direita do ícone), como na referência. Topo com busca, sino de alertas e avatar.
**Grade:** 1 coluna no celular, 2 a partir de `md`, 12 colunas a partir de `lg`.

## 6. Formas e bordas

| Elemento | Raio |
|---|---|
| Card | 16 px (`rounded-2xl`) |
| Botão, campo, linha de lista | 12 px (`rounded-xl`) |
| Selo, chip, aba ativa | 9999 px |
| Item de menu, pequeno | 8 px |

Card: fundo `branco`, borda 1 px `neutro-100`. Campo em repouso: borda `neutro-200`; foco: borda `azul-500` e anel de foco; erro: borda `vermelho-500`.

## 7. Elevação e movimento

| Nível | Sombra | Uso |
|---|---|---|
| 1 | `0 1px 2px rgba(18,33,79,.04), 0 4px 16px rgba(18,33,79,.06)` | Cards |
| 2 | `0 8px 24px rgba(18,33,79,.12)` | Menus, popovers, toast |
| 3 | `0 16px 40px rgba(18,33,79,.18)` | Diálogo |

Movimento: `rapido` 120 ms, `base` 200 ms, `lento` 300 ms; easing padrão `cubic-bezier(.4, 0, .2, 1)`. Botão pressionado: escala 0,98. Troca de status: *fade* de 200 ms. Respeitar `prefers-reduced-motion` (desliga animações não essenciais).

## 8. Acessibilidade

- Contraste do §3.6; foco visível em todo controle (anel de 2 px `azul-400`, com 2 px de afastamento).
- Alvo de toque de 44 × 44 px; navegação por teclado completa; `aria-label` em botão só com ícone; `aria-live="polite"` na confirmação de entrega e `aria-live="assertive"` no alerta de parada de emergência.
- Status por cor + ícone/texto (regra de ouro 4).

## 9. Ícones

Biblioteca única: **Lucide** (versão do projeto; confirmar os nomes na versão instalada).

| Uso | Ícone |
|---|---|
| Robô | `Bot` |
| Farmácia / medicamento | `Pill` |
| Banco de sangue | `Droplet` |
| Estoque | `Boxes` |
| Solicitar | `PackagePlus` |
| Entrega concluída | `PackageCheck` |
| Local | `MapPin` |
| Histórico | `History` |
| Bateria | `BatteryMedium` |
| Alerta | `TriangleAlert` |
| Emergência | `Siren` |
| UTI | `HeartPulse` |
| Consultório | `Stethoscope` |

Tamanhos: 16 (em texto), 20 (em campo e botão), 24 (barra de navegação).

## 10. Componentes base

| Componente | Especificação resumida |
|---|---|
| `Button` | Variantes: `primario` (azul-500, texto branco), `secundario` (branco, borda neutro-200, texto tinta), `fantasma` (texto azul-600), `perigo` (vermelho-500, texto branco). Tamanhos: `sm` 36, `md` 44 (padrão), `lg` 52. Raio 12, peso 600 |
| `Input`, `Select`, `Textarea` | Altura 44, raio 12, borda neutro-200; foco azul-500; erro vermelho-500 com mensagem abaixo; rótulo acima em `texto-sm` peso 500 |
| `Card` | Fundo branco, borda neutro-100, raio 16, sombra nível 1, padding 16 (celular) ou 20 |
| `Badge` | Pílula, `texto-sm`, ponto de 6 px à esquerda, cores do §3.5 |
| `Tabs` | Abas de texto com sublinhado azul-500 de 2 px na ativa |
| `Table` | Cabeçalho `texto-sm` neutro-500; linhas com divisória neutro-100; no celular vira lista de cards |
| `Dialog` e `Toast` | Sombra nível 3 e 2; `Toast` some em 4 s; erro nunca some sozinho |
| `EmptyState` | Ícone de 40, título `texto-lg`, uma linha de apoio e um botão com verbo ("Solicitar medicamento") |
| `Skeleton` | Base neutro-50 com brilho para neutro-100 |
| `Sidebar`, `BottomNav`, `TopBar`, `PageHeader` | Layout do §5; `PageHeader` com título `texto-2xl`, subtítulo em neutro-500 e ações à direita |

## 11. Componentes de domínio

**`PriorityBadge`** — `critica | media | rotina`; cores e rótulos do §3.5 ("Crítica", "Média", "Rotina").

**`StatusBadge`** — estados do §3.5, com ícone e texto.

**`StatCard`** — cartão de destaque em azul sólido (`azul-500`, texto branco).
```
┌─────────────────────────────┐
│ Entregas hoje               │  texto-sm
│ 12                          │  texto-4xl, peso 700, tabular-nums
│ 9 concluídas · 2 em curso   │  texto-xs
└─────────────────────────────┘
```
Também existe a variante branca (card normal) com selo de variação.

**`RobotStatusCard`** — nome, `StatusBadge` do estado, destino, tempo estimado e barra de bateria (azul; vermelho abaixo de 20%).

**`DeliveryQueueRow`** — linha arredondada com horário, itens e `origem → destino`, e `PriorityBadge` à direita.
```
09:20  Sangue, 2 bolsas · Banco de sangue → Centro cirúrgico     [Crítica]
```
No celular, o selo desce para a segunda linha.

**`StockLevelBar`** — item e local, quantidade (`tabular-nums`), barra com o nível do §3.5 e o texto "Abaixo do mínimo" quando for o caso.

**`MovementLogRow`** — data e hora, tipo (reserva, baixa, crédito, estorno), item, quantidade com sinal, local, entrega relacionada.

**`AlertBanner`** — largura total, `vermelho-50` com borda `vermelho-200`, ícone `TriangleAlert` e texto em `vermelho-600` (ex.: "Corredor norte bloqueado. Rota recalculada pela cruz central."). Variante informativa em azul-50.

**`TelemetryPanel`** — mapa simples com o robô, a rota e os obstáculos, mais pose e velocidade. Usa as cores do azul (rota) e do vermelho (obstáculo).

**`RequestForm`** — formulário mobile-first de "Solicitar medicamento": busca de item, quantidade, prioridade (três opções com `PriorityBadge`), destino (padrão = local do usuário, editável), saldo da origem visível e botão primário "Solicitar medicamento". Prioridade crítica mostra o aviso de que exige a assinatura do farmacêutico.

## 12. Implementação

```
design-system/
├── tokens/tokens.json        # fonte única
├── tokens/build.mjs          # gera dist/
├── dist/tokens.css           # CSS variables em :root
├── dist/tailwind.preset.cjs  # cores, fontes, raios, sombras, breakpoints
├── dist/GeraldoTokens.cs     # Color32 estáticos para o Unity
├── css/components.css        # (opcional) classes .gd-* para quem não usa Tailwind
├── showcase/                 # página de componentes e estados
├── tests/                    # contraste e "sem hex solto"
└── DESIGN_SYSTEM.md          # guia de referência (pessoas e IAs)
```

Fluxo: o `tokens.json` é editado, `node design-system/tokens/build.mjs` regenera os três arquivos de `dist/` (que são versionados), e o app web e o Unity só leem de `dist/`. Ninguém edita `dist/` à mão.

**Testes automáticos (CI):**
1. Todos os pares de texto e fundo usados pelos componentes atingem o contraste do §3.6.
2. Nenhum arquivo do app web contém cor em hex fora de `dist/` e de `tokens.json`.

## 13. Critérios de pronto da v0 (sáb 07/11 a dom 08/11)

- `tokens.json` completo com as tabelas dos §3 a §7 e `build.mjs` gerando os três arquivos de `dist/`.
- `DESIGN_SYSTEM.md` publicado, com as regras de ouro do §2 no começo.
- Vieira consegue montar `Button`, `Card`, `PriorityBadge` e `StatCard` usando só `dist/`.
