# web/AGENTS.md — sistema web responsivo (dono: Vieira)

Stack: React + Vite + TypeScript + Tailwind v3, Vitest + Testing Library, MSW para simular a API. Os padrões de projeto da disciplina ficam em `src/domain/` e `src/apresentacao/`; siga o padrão que já existe lá. Guia geral: [`docs/padroes-de-projeto.md`](../docs/padroes-de-projeto.md) (Adapter, Observer, Builder, Strategy e funções puras já estão aplicados; novas telas reaproveitam esses blocos).

## Comandos

```bash
cd web
npm install
npm test -- --run
npm run dev
npm run build
```

## Regras (do design system)

- **Sem hex solto:** só classes do preset (`bg-azul-500`, `text-vermelho-600`, `rounded-card`...) ou `var(--azul-500)`.
- **Vermelho só para:** prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro.
- **Um botão primário por tela.** Status nunca só por cor: sempre cor + ícone ou texto.
- **Mobile-first;** alvo de toque mínimo de 44 px (`min-h-controle`).
- Números com `tabular-nums`. Texto em português, *sentence case*, botão com verbo curto ("Solicitar medicamento"), sem "por favor".
- Ícones: `lucide-react`.

## Dados

Consuma só a API do contrato (`docs/contracts/openapi.yaml`). Enquanto o backend não estiver pronto, use os handlers MSW em `src/api/mocks/`.
