# G.E.R.A.L.D.O. — Semana 1 (Vieira): sistema web responsivo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ter o app web com login, a tela "Solicitar medicamento" (mobile-first) funcionando contra a API (ou contra a API simulada nos testes), e os componentes base e de domínio do design system implementados só com os tokens.

**Architecture:** App React + Vite + TypeScript. As cores, fontes, raios e sombras vêm exclusivamente do preset do Tailwind gerado em `design-system/dist/`. A comunicação com o backend passa por um cliente fino (`src/api/client.ts`) com os tipos do contrato (`src/api/types.ts`). Nos testes, a API é simulada com MSW (as mesmas respostas do contrato), então a web se desenvolve sem esperar o backend.

**Tech Stack:** React, Vite, TypeScript, Tailwind CSS v3, Vitest + Testing Library + user-event, MSW 3, lucide-react.

**Versões com que este plano foi validado (05/11/2026):** React 19.3, Vite 8.3, TypeScript 7.0, Vitest 5.1, Tailwind 3.4, MSW 3.0, lucide-react 1.69, Testing Library React 16.3 / user-event 14.6 / jest-dom 7.0, jsdom 31. Se uma versão nova quebrar algo, fixe a que estiver nesta lista.

**Spec:** `docs/superpowers/specs/2026-11-05-geraldo-design-system-design.md` e `docs/superpowers/specs/2026-11-05-geraldo-plano-desenvolvimento-design.md` (seção 4.3); contrato: `docs/contracts/openapi.yaml`.

**Pré-requisitos:** tokens do design system em `design-system/dist/` (Tarefa 5 do plano de fundação do Samuel; disponível sábado 07/11). A Tarefa 1 deste plano só precisa do preset; se ele ainda não existir, espere o aviso do Samuel.

**Decisão sua (até 07/11):** este plano assume React + Vite + TypeScript + Tailwind v3. Se o grupo preferir outra stack, avise o Samuel antes de começar: os tokens (`tokens.css`) valem em qualquer uma.

## Global Constraints

- **Sem hex solto:** cores só pelas classes do preset (`bg-azul-500`, `text-vermelho-700`, `rounded-card`, `shadow-card`...) ou `var(--azul-500)` (DS §2).
- **Vermelho só para:** prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro (DS §2).
- **Um botão primário por tela;** status nunca só por cor: sempre cor + ícone ou texto (DS §2).
- **Mobile-first;** controles com no mínimo 44 px de altura (`min-h-controle`) (DS §2, §5).
- Números com `tabular-nums`; texto de interface em português, *sentence case*, botão com verbo curto, sem "por favor" e sem ponto final em rótulos e títulos (DS §2).
- Cantos: card `rounded-card` (16 px), controles `rounded-controle` (12 px), selos `rounded-full` (DS §6).
- Ícones: `lucide-react`; 16 px em texto, 20 px em botão e campo, 24 px na navegação (DS §9).
- Consumir só a API do contrato; não criar endpoint nem campo novo. Mudança de contrato só por PR com aviso ao Samuel.
- Sem segredos no repositório; a URL da API vem de `VITE_API_URL` (padrão `http://localhost:8000`).
- Branch `feat/web-<assunto>`; commits em português, curtos; nada direto na `main`.

---

### Task 1: Projeto web com Tailwind e os tokens

**Files:**
- Create: `web/package.json`, `web/index.html`, `web/vite.config.ts`, `web/tsconfig.json`, `web/postcss.config.cjs`, `web/tailwind.config.cjs`
- Create: `web/src/main.tsx`, `web/src/App.tsx`, `web/src/index.css`, `web/src/vite-env.d.ts`, `web/src/test/setup.ts`
- Test: `web/src/App.test.tsx`

**Interfaces:**
- Consumes: `design-system/dist/tailwind.preset.cjs` e `design-system/dist/tokens.css`.
- Produces: projeto que roda `npm run dev`, `npm test`, `npm run build`; classes do preset disponíveis (`bg-azul-500`, `rounded-card`, `min-h-controle`, `font-display`...).

- [ ] **Step 1: Criar o projeto**

```bash
cd web
cat > package.json <<'EOF'
{
  "name": "geraldo-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "test": "vitest"
  }
}
EOF
npm install react react-dom lucide-react
npm install -D vite @vitejs/plugin-react typescript @types/react @types/react-dom \
  tailwindcss@3 postcss autoprefixer \
  vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event msw@3
```

- [ ] **Step 2: Escrever o teste de fumaça (falha primeiro)**

Create `web/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import App from "./App";

test("mostra o nome do sistema", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "G.E.R.A.L.D.O." })).toBeInTheDocument();
});
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `npm test -- --run`
Expected: FAIL (sem configuração e sem `App`).

- [ ] **Step 4: Escrever a configuração**

`web/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", globals: true, setupFiles: "./src/test/setup.ts", css: false },
});
```

`web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "skipLibCheck": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

`web/postcss.config.cjs`:

```js
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

`web/tailwind.config.cjs`:

```js
module.exports = {
  presets: [require("../design-system/dist/tailwind.preset.cjs")],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
};
```

`web/index.html`:

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>G.E.R.A.L.D.O.</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`web/src/index.css`:

```css
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap");
@import "../../design-system/dist/tokens.css";

@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-fundo font-sans text-tinta;
}
```

`web/src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />
```

`web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

`web/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`web/src/App.tsx` (provisório; a Tarefa 6 o substitui):

```tsx
export default function App() {
  return (
    <main className="p-4">
      <h1 className="font-display text-2xl font-bold">G.E.R.A.L.D.O.</h1>
    </main>
  );
}
```

- [ ] **Step 5: Rodar e ver passar**

Run: `npm test -- --run && npm run build`
Expected: `1 passed` e o build termina sem erro de TypeScript. Confira no `dist/assets/*.css` (ou rodando `npm run dev`) que o CSS inclui as variáveis do `tokens.css` (por exemplo `--azul-500`).

- [ ] **Step 6: Commit**

```bash
cd ..
git add web
git commit -m "feat(web): projeto React + Vite + Tailwind com os tokens do design system"
```

---

### Task 2: `Button` e `Card`

**Files:**
- Create: `web/src/components/Button.tsx`, `web/src/components/Card.tsx`
- Test: `web/src/components/Button.test.tsx`, `web/src/components/Card.test.tsx`

**Interfaces:**
- Produces:
  - `Button({ variant?: "primario"|"secundario"|"fantasma"|"perigo", size?: "sm"|"md"|"lg", ...ButtonHTMLAttributes })` (padrão `primario`, `md`, `type="button"`).
  - `Card({ ...HTMLAttributes<HTMLDivElement> })`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

`web/src/components/Button.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

test("é um botão do tipo button e dispara o onClick", async () => {
  const onClick = vi.fn();
  render(<Button onClick={onClick}>Solicitar medicamento</Button>);
  const button = screen.getByRole("button", { name: "Solicitar medicamento" });
  expect(button).toHaveAttribute("type", "button");
  await userEvent.click(button);
  expect(onClick).toHaveBeenCalledTimes(1);
});

test("a variante primária usa azul-500 e a de perigo usa vermelho-500", () => {
  render(
    <>
      <Button>Primário</Button>
      <Button variant="perigo">Perigo</Button>
    </>,
  );
  expect(screen.getByRole("button", { name: "Primário" })).toHaveClass("bg-azul-500", "text-branco");
  expect(screen.getByRole("button", { name: "Perigo" })).toHaveClass("bg-vermelho-500", "text-branco");
});

test("o tamanho padrão tem altura mínima de toque de 44 px", () => {
  render(<Button>Ok</Button>);
  expect(screen.getByRole("button")).toHaveClass("min-h-controle", "rounded-controle");
});

test("desabilitado não dispara o clique", async () => {
  const onClick = vi.fn();
  render(
    <Button disabled onClick={onClick}>
      Enviar
    </Button>,
  );
  await userEvent.click(screen.getByRole("button"));
  expect(onClick).not.toHaveBeenCalled();
});
```

`web/src/components/Card.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

test("é um cartão branco com cantos de 16 px, borda fina e sombra do nível 1", () => {
  render(<Card data-testid="card">Conteúdo</Card>);
  expect(screen.getByTestId("card")).toHaveClass("bg-branco", "rounded-card", "border", "border-neutro-100", "shadow-card");
  expect(screen.getByText("Conteúdo")).toBeInTheDocument();
});

test("aceita className extra sem perder o estilo base", () => {
  render(<Card data-testid="card" className="mt-4">x</Card>);
  expect(screen.getByTestId("card")).toHaveClass("mt-4", "rounded-card");
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run (em `web/`): `npm test -- --run`
Expected: FAIL (componentes não existem).

- [ ] **Step 3: Implementar**

`web/src/components/Button.tsx`:

```tsx
import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primario" | "secundario" | "fantasma" | "perigo";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  primario: "bg-azul-500 text-branco hover:bg-azul-600",
  secundario: "bg-branco text-tinta border border-neutro-200 hover:bg-neutro-50",
  fantasma: "bg-transparent text-azul-600 hover:bg-azul-50",
  perigo: "bg-vermelho-500 text-branco hover:bg-vermelho-600",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "min-h-[36px] px-4 text-sm",
  md: "min-h-controle px-5 text-base",
  lg: "min-h-[52px] px-6 text-base",
};

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-controle font-sans font-semibold transition active:scale-[0.98] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-azul-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize };

export function Button({ variant = "primario", size = "md", className = "", type = "button", ...rest }: Props) {
  return <button type={type} className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`} {...rest} />;
}
```

`web/src/components/Card.tsx`:

```tsx
import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-card border border-neutro-100 bg-branco p-4 shadow-card md:p-5 ${className}`} {...rest} />;
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `npm test -- --run`
Expected: todos passam (`1 + 4 + 2 = 7 passed`).

- [ ] **Step 5: Commit**

```bash
cd ..
git add web
git commit -m "feat(web): Button e Card"
```

---

### Task 3: Tipos do contrato e componentes de domínio

**Files:**
- Create: `web/src/api/types.ts`, `web/src/components/PriorityBadge.tsx`, `web/src/components/StatusBadge.tsx`, `web/src/components/StatCard.tsx`
- Test: `web/src/components/PriorityBadge.test.tsx`, `web/src/components/StatusBadge.test.tsx`, `web/src/components/StatCard.test.tsx`

**Interfaces:**
- Produces:
  - `src/api/types.ts`: `Priority`, `DeliveryStatus`, `Role`, `Me`, `Location`, `StockEntry`, `DeliveryItem`, `DeliveryCreate`, `Delivery` (espelham `docs/contracts/openapi.yaml`).
  - `PriorityBadge({ priority })` → texto "Crítica", "Média" ou "Rotina".
  - `StatusBadge({ status })` → rótulo em português com ícone (`aria-hidden`).
  - `StatCard({ label, value, caption?, variant?: "destaque"|"branco" })`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

`web/src/components/PriorityBadge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { PriorityBadge } from "./PriorityBadge";

test.each([
  ["critica", "Crítica", ["bg-vermelho-100", "text-vermelho-700"]],
  ["media", "Média", ["bg-azul-100", "text-azul-700"]],
  ["rotina", "Rotina", ["bg-neutro-50", "text-neutro-600"]],
] as const)("prioridade %s mostra %s com as cores do design system", (priority, label, classes) => {
  render(<PriorityBadge priority={priority} />);
  expect(screen.getByText(label)).toHaveClass(...classes, "rounded-full");
});
```

`web/src/components/StatusBadge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import type { DeliveryStatus } from "../api/types";
import { StatusBadge } from "./StatusBadge";

const CASES: [DeliveryStatus, string, string][] = [
  ["PENDENTE_APROVACAO", "Aguardando aprovação", "bg-aviso-50"],
  ["NA_FILA", "Na fila", "bg-neutro-50"],
  ["EM_ROTA", "A caminho", "bg-azul-100"],
  ["AGUARDANDO_RECEBIMENTO", "Aguardando recebimento", "bg-azul-100"],
  ["ENTREGUE", "Entregue", "bg-sucesso-50"],
  ["CANCELADA", "Cancelada", "bg-neutro-50"],
  ["FALHOU", "Falhou", "bg-vermelho-100"],
];

test.each(CASES)("%s mostra %s com texto e ícone (nunca só cor)", (status, label, bg) => {
  const { container } = render(<StatusBadge status={status} />);
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(container.firstElementChild).toHaveClass(bg);
  expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
});

test("cancelada aparece riscada", () => {
  render(<StatusBadge status="CANCELADA" />);
  expect(screen.getByText("Cancelada")).toHaveClass("line-through");
});
```

`web/src/components/StatCard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { StatCard } from "./StatCard";

test("o cartão de destaque é azul sólido com o número em tabular-nums", () => {
  const { container } = render(<StatCard label="Entregas hoje" value={12} caption="9 concluídas · 2 em curso" />);
  expect(container.firstElementChild).toHaveClass("bg-azul-500", "text-branco", "rounded-card");
  expect(screen.getByText("Entregas hoje")).toBeInTheDocument();
  expect(screen.getByText("12")).toHaveClass("tabular-nums", "font-display", "text-4xl");
  expect(screen.getByText("9 concluídas · 2 em curso")).toBeInTheDocument();
});

test("a variante branca usa fundo branco e borda", () => {
  const { container } = render(<StatCard label="Na fila" value="3" variant="branco" />);
  expect(container.firstElementChild).toHaveClass("bg-branco", "border-neutro-100");
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `npm test -- --run`
Expected: FAIL (arquivos não existem).

- [ ] **Step 3: Implementar tipos e componentes**

`web/src/api/types.ts`:

```ts
// Espelha docs/contracts/openapi.yaml. Mudança de contrato só por PR com aviso ao Samuel.
export type Priority = "critica" | "media" | "rotina";
export type Role = "medico" | "enfermeiro" | "farmaceutico" | "admin" | "robo";
export type DeliveryStatus =
  | "PENDENTE_APROVACAO"
  | "NA_FILA"
  | "EM_ROTA"
  | "AGUARDANDO_RECEBIMENTO"
  | "ENTREGUE"
  | "CANCELADA"
  | "FALHOU";

export interface Me {
  id: number;
  username: string;
  role: Role;
  local_id: string | null;
}

export interface Location {
  id: string;
  name: string;
  kind: string;
  has_stock: boolean;
  waypoint: string | null;
}

export interface StockEntry {
  location_id: string;
  item_id: string;
  item_name: string;
  quantity: number;
  reserved: number;
  minimum: number;
}

export interface DeliveryItem {
  item_id: string;
  quantity: number;
}

export interface DeliveryCreate {
  origin_id: string;
  dest_id?: string | null;
  items: DeliveryItem[];
  priority: Priority;
}

export interface Delivery {
  id: number;
  origin_id: string;
  dest_id: string;
  items: DeliveryItem[];
  priority: Priority;
  status: DeliveryStatus;
  requested_by: number;
  created_at: string;
}
```

`web/src/components/PriorityBadge.tsx`:

```tsx
import type { Priority } from "../api/types";

const STYLES: Record<Priority, { label: string; box: string; dot: string }> = {
  critica: { label: "Crítica", box: "bg-vermelho-100 text-vermelho-700", dot: "bg-vermelho-500" },
  media: { label: "Média", box: "bg-azul-100 text-azul-700", dot: "bg-azul-500" },
  rotina: { label: "Rotina", box: "bg-neutro-50 text-neutro-600", dot: "bg-neutro-400" },
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  const s = STYLES[priority];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${s.box}`}>
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}
```

(O teste procura o texto "Crítica" e espera as classes no elemento que contém o texto: como o texto fica direto no `<span>` externo, `getByText` devolve esse elemento.)

`web/src/components/StatusBadge.tsx`:

```tsx
import { Ban, Bot, CircleCheck, Clock, PackageCheck, ShieldCheck, TriangleAlert, type LucideIcon } from "lucide-react";
import type { DeliveryStatus } from "../api/types";

const STATUS: Record<DeliveryStatus, { label: string; box: string; Icon: LucideIcon }> = {
  PENDENTE_APROVACAO: { label: "Aguardando aprovação", box: "bg-aviso-50 text-aviso-700", Icon: ShieldCheck },
  NA_FILA: { label: "Na fila", box: "bg-neutro-50 text-neutro-600", Icon: Clock },
  EM_ROTA: { label: "A caminho", box: "bg-azul-100 text-azul-700", Icon: Bot },
  AGUARDANDO_RECEBIMENTO: { label: "Aguardando recebimento", box: "bg-azul-100 text-azul-700", Icon: PackageCheck },
  ENTREGUE: { label: "Entregue", box: "bg-sucesso-50 text-sucesso-700", Icon: CircleCheck },
  CANCELADA: { label: "Cancelada", box: "bg-neutro-50 text-neutro-600", Icon: Ban },
  FALHOU: { label: "Falhou", box: "bg-vermelho-100 text-vermelho-700", Icon: TriangleAlert },
};

export function StatusBadge({ status }: { status: DeliveryStatus }) {
  const { label, box, Icon } = STATUS[status];
  const strike = status === "CANCELADA" ? "line-through" : "";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${box}`}>
      <Icon size={16} aria-hidden="true" />
      <span className={strike}>{label}</span>
    </span>
  );
}
```

`web/src/components/StatCard.tsx`:

```tsx
import type { ReactNode } from "react";

type Props = { label: string; value: ReactNode; caption?: string; variant?: "destaque" | "branco" };

const VARIANTS = {
  destaque: "bg-azul-500 text-branco",
  branco: "bg-branco text-tinta border border-neutro-100 shadow-card",
};

export function StatCard({ label, value, caption, variant = "destaque" }: Props) {
  return (
    <div className={`rounded-card p-5 ${VARIANTS[variant]}`}>
      <p className="text-sm">{label}</p>
      <p className="font-display text-4xl font-bold tabular-nums">{value}</p>
      {caption && <p className="text-xs">{caption}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `npm test -- --run`
Expected: `20 passed`. Se algum ícone do Lucide não existir na versão instalada (erro "is not exported" ou elemento `undefined`), troque pelo equivalente mais próximo da lista de ícones da DS §9 e anote no PR.

- [ ] **Step 5: Commit**

```bash
cd ..
git add web
git commit -m "feat(web): tipos do contrato, PriorityBadge, StatusBadge e StatCard"
```

---

### Task 4: Cliente da API e API simulada (MSW)

**Files:**
- Create: `web/src/api/client.ts`, `web/src/api/mocks/fixtures.ts`, `web/src/api/mocks/handlers.ts`, `web/src/api/mocks/server.ts`
- Modify: `web/src/test/setup.ts`
- Test: `web/src/api/client.test.ts`

**Interfaces:**
- Consumes: tipos da Tarefa 3.
- Produces:
  - `api.login(username, password)`, `api.me()`, `api.locations()`, `api.stock(locationId?)`, `api.createDelivery(body)`, `api.deliveries()`; `setToken(token | null)`; `ApiError(status, message)`.
  - `src/api/mocks/fixtures.ts`: `ME`, `LOCATIONS`, `STOCK` (usados nos testes de componentes); `server` (MSW) já ligado no `setup.ts`.
  - A senha aceita pelo mock de login é `demo`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

`web/src/api/client.test.ts`:

```ts
import { http, HttpResponse } from "msw";
import { api, ApiError, setToken } from "./client";
import { ME } from "./mocks/fixtures";
import { server } from "./mocks/server";

afterEach(() => setToken(null));

test("login devolve o token", async () => {
  const res = await api.login("medico1", "demo");
  expect(res.access_token).toBe("token-de-teste");
});

test("login com senha errada levanta ApiError com a mensagem da API", async () => {
  await expect(api.login("medico1", "errada")).rejects.toMatchObject({
    status: 401,
    message: "Usuário ou senha incorretos. Tente de novo.",
  });
});

test("envia o token no cabeçalho Authorization", async () => {
  let header: string | null = null;
  server.use(
    http.get("http://localhost:8000/me", ({ request }) => {
      header = request.headers.get("authorization");
      return HttpResponse.json(ME);
    }),
  );
  setToken("abc");
  await api.me();
  expect(header).toBe("Bearer abc");
});

test("stock filtra por local", async () => {
  const entries = await api.stock("farmacia");
  expect(entries.length).toBeGreaterThan(0);
  expect(entries.every((e) => e.location_id === "farmacia")).toBe(true);
});

test("createDelivery manda o corpo e devolve a entrega criada", async () => {
  const delivery = await api.createDelivery({
    origin_id: "farmacia",
    dest_id: null,
    items: [{ item_id: "dipirona-500mg", quantity: 5 }],
    priority: "media",
  });
  expect(delivery).toMatchObject({ origin_id: "farmacia", dest_id: "consultorio1", status: "NA_FILA", priority: "media" });
});

test("erro sem corpo JSON vira ApiError com mensagem padrão", async () => {
  server.use(http.get("http://localhost:8000/locations", () => new HttpResponse("falhou", { status: 500 })));
  const err = await api.locations().catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(500);
  expect(err.message).toBe("Algo deu errado. Tente de novo.");
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `npm test -- --run`
Expected: FAIL (`client` e `mocks` não existem).

- [ ] **Step 3: Implementar o cliente e os mocks**

`web/src/api/client.ts`:

```ts
import type { Delivery, DeliveryCreate, Location, Me, StockEntry } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
let token: string | null = null;

export function setToken(value: string | null): void {
  token = value;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Algo deu errado. Tente de novo.");
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: "bearer" }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<Me>("/me"),
  locations: () => request<Location[]>("/locations"),
  stock: (locationId?: string) =>
    request<StockEntry[]>(`/stock${locationId ? `?location_id=${encodeURIComponent(locationId)}` : ""}`),
  createDelivery: (body: DeliveryCreate) =>
    request<Delivery>("/deliveries", { method: "POST", body: JSON.stringify(body) }),
  deliveries: () => request<Delivery[]>("/deliveries"),
};
```

`web/src/api/mocks/fixtures.ts`:

```ts
import type { Location, Me, StockEntry } from "../types";

export const ME: Me = { id: 1, username: "medico1", role: "medico", local_id: "consultorio1" };

export const LOCATIONS: Location[] = [
  { id: "farmacia", name: "Farmácia central", kind: "pharmacy", has_stock: true, waypoint: "farmacia_balcao" },
  { id: "banco_sangue", name: "Banco de sangue", kind: "blood_bank", has_stock: true, waypoint: "banco_sangue_retirada" },
  { id: "consultorio1", name: "Consultório 1", kind: "office", has_stock: true, waypoint: "cons1_entrega" },
  { id: "consultorio2", name: "Consultório 2", kind: "office", has_stock: true, waypoint: "cons2_entrega" },
  { id: "enfermaria214", name: "Enfermaria 214", kind: "ward", has_stock: true, waypoint: "enf214_entrega" },
  { id: "recepcao", name: "Recepção", kind: "reception", has_stock: false, waypoint: null },
];

export const STOCK: StockEntry[] = [
  { location_id: "farmacia", item_id: "dipirona-500mg", item_name: "Dipirona 500 mg", quantity: 420, reserved: 0, minimum: 100 },
  { location_id: "farmacia", item_id: "amoxicilina-500mg", item_name: "Amoxicilina 500 mg", quantity: 200, reserved: 200, minimum: 60 },
  { location_id: "banco_sangue", item_id: "bolsa-sangue-o-neg", item_name: "Bolsa de sangue O negativo", quantity: 6, reserved: 0, minimum: 10 },
];
```

(A amoxicilina tem tudo reservado de propósito: o formulário não deve oferecer item sem saldo disponível.)

`web/src/api/mocks/handlers.ts`:

```ts
import { http, HttpResponse } from "msw";
import type { DeliveryCreate } from "../types";
import { LOCATIONS, ME, STOCK } from "./fixtures";

const BASE = "http://localhost:8000";

export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const { password } = (await request.json()) as { username: string; password: string };
    if (password !== "demo") {
      return HttpResponse.json({ detail: "Usuário ou senha incorretos. Tente de novo." }, { status: 401 });
    }
    return HttpResponse.json({ access_token: "token-de-teste", token_type: "bearer" });
  }),
  http.get(`${BASE}/me`, () => HttpResponse.json(ME)),
  http.get(`${BASE}/locations`, () => HttpResponse.json(LOCATIONS)),
  http.get(`${BASE}/stock`, ({ request }) => {
    const locationId = new URL(request.url).searchParams.get("location_id");
    return HttpResponse.json(locationId ? STOCK.filter((s) => s.location_id === locationId) : STOCK);
  }),
  http.post(`${BASE}/deliveries`, async ({ request }) => {
    const body = (await request.json()) as DeliveryCreate;
    return HttpResponse.json(
      {
        id: 1,
        origin_id: body.origin_id,
        dest_id: body.dest_id ?? ME.local_id,
        items: body.items,
        priority: body.priority,
        status: body.priority === "critica" ? "PENDENTE_APROVACAO" : "NA_FILA",
        requested_by: ME.id,
        created_at: "2026-11-09T10:00:00Z",
      },
      { status: 201 },
    );
  }),
  http.get(`${BASE}/deliveries`, () => HttpResponse.json([])),
];
```

`web/src/api/mocks/server.ts`:

```ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
```

Replace `web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "../api/mocks/server";

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] **Step 4: Rodar e ver passar**

Run: `npm test -- --run`
Expected: `26 passed`.

- [ ] **Step 5: Commit**

```bash
cd ..
git add web
git commit -m "feat(web): cliente da API do contrato e API simulada com MSW"
```

---

### Task 5: Formulário "Solicitar medicamento" (mobile-first)

**Files:**
- Create: `web/src/components/RequestForm.tsx`, `web/src/pages/SolicitarPage.tsx`
- Test: `web/src/components/RequestForm.test.tsx`, `web/src/pages/SolicitarPage.test.tsx`

**Interfaces:**
- Consumes: `Button`, `Card`, `api`, `setToken`, fixtures (Tarefas 2 a 4).
- Produces:
  - `RequestForm({ locations, defaultDestId, loadStock, onSubmit })`: `loadStock(originId) => Promise<StockEntry[]>` (precisa ser **estável** entre renders, use `useCallback`); `onSubmit(body: DeliveryCreate) => Promise<void>`. Lista só itens com saldo disponível (`quantity - reserved > 0`) no formato "Nome (N disponíveis)".
  - `SolicitarPage()`: carrega `/me` e `/locations`, mostra o formulário e a mensagem "Entrega solicitada. Acompanhe em Minhas entregas." após o sucesso.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

`web/src/components/RequestForm.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LOCATIONS, STOCK } from "../api/mocks/fixtures";
import { RequestForm } from "./RequestForm";

const loadStock = vi.fn(async (originId: string) => STOCK.filter((s) => s.location_id === originId));

function setup(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  render(<RequestForm locations={LOCATIONS} defaultDestId="consultorio1" loadStock={loadStock} onSubmit={onSubmit} />);
  return onSubmit;
}

beforeEach(() => loadStock.mockClear());

test("carrega o estoque da farmácia e lista só o que tem saldo disponível", async () => {
  setup();
  expect(await screen.findByRole("option", { name: "Dipirona 500 mg (420 disponíveis)" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /Amoxicilina/ })).not.toBeInTheDocument();
  expect(loadStock).toHaveBeenCalledWith("farmacia");
});

test("o destino já vem preenchido com o local do usuário e não oferece locais sem ponto de parada", async () => {
  setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  expect(screen.getByLabelText("Destino")).toHaveValue("consultorio1");
  expect(screen.queryByRole("option", { name: "Recepção" })).not.toBeInTheDocument();
});

test("envia o pedido com a quantidade, o destino padrão e a prioridade média", async () => {
  const onSubmit = setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  const quantity = screen.getByLabelText("Quantidade");
  await userEvent.clear(quantity);
  await userEvent.type(quantity, "5");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(onSubmit).toHaveBeenCalledWith({
    origin_id: "farmacia",
    dest_id: "consultorio1",
    items: [{ item_id: "dipirona-500mg", quantity: 5 }],
    priority: "media",
  });
});

test("quantidade zero mostra o erro e não envia", async () => {
  const onSubmit = setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  const quantity = screen.getByLabelText("Quantidade");
  await userEvent.clear(quantity);
  await userEvent.type(quantity, "0");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Informe uma quantidade maior que zero.");
  expect(onSubmit).not.toHaveBeenCalled();
});

test("origem igual ao destino mostra o erro e não envia", async () => {
  const onSubmit = setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.selectOptions(screen.getByLabelText("Destino"), "farmacia");
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Origem e destino precisam ser diferentes.");
  expect(onSubmit).not.toHaveBeenCalled();
});

test("prioridade crítica avisa que exige a assinatura do farmacêutico", async () => {
  setup();
  await screen.findByRole("option", { name: /Dipirona/ });
  expect(screen.queryByText(/assinatura do farmacêutico/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText("Crítica"));
  expect(screen.getByText("Prioridade crítica exige a assinatura do farmacêutico.")).toBeInTheDocument();
});

test("mostra a mensagem de erro devolvida pela API", async () => {
  const onSubmit = vi.fn().mockRejectedValue(new Error("Estoque insuficiente de dipirona-500mg em farmacia."));
  setup(onSubmit);
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Estoque insuficiente de dipirona-500mg em farmacia.");
});
```

`web/src/pages/SolicitarPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setToken } from "../api/client";
import { SolicitarPage } from "./SolicitarPage";

afterEach(() => setToken(null));

test("carrega o usuário e os locais, envia o pedido e confirma", async () => {
  setToken("token-de-teste");
  render(<SolicitarPage />);
  expect(await screen.findByRole("heading", { name: "Solicitar medicamento" })).toBeInTheDocument();
  await screen.findByRole("option", { name: /Dipirona/ });
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega solicitada. Acompanhe em Minhas entregas.");
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `npm test -- --run`
Expected: FAIL (componentes não existem).

- [ ] **Step 3: Implementar o formulário**

`web/src/components/RequestForm.tsx`:

```tsx
import { useEffect, useState, type FormEvent } from "react";
import type { DeliveryCreate, Location, Priority, StockEntry } from "../api/types";
import { Button } from "./Button";

const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "critica", label: "Crítica" },
  { value: "media", label: "Média" },
  { value: "rotina", label: "Rotina" },
];

const FIELD =
  "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 text-base text-tinta " +
  "focus:border-azul-500 focus:outline-none focus:ring-2 focus:ring-azul-200";
const LABEL = "mb-1 block text-sm font-medium text-neutro-700";

interface Props {
  locations: Location[];
  defaultDestId: string | null;
  loadStock: (originId: string) => Promise<StockEntry[]>;
  onSubmit: (body: DeliveryCreate) => Promise<void>;
}

export function RequestForm({ locations, defaultDestId, loadStock, onSubmit }: Props) {
  const places = locations.filter((l) => l.waypoint);
  const origins = places.filter((l) => l.has_stock);
  const [originId, setOriginId] = useState(origins.find((l) => l.id === "farmacia")?.id ?? origins[0]?.id ?? "");
  const [destId, setDestId] = useState(defaultDestId ?? "");
  const [stock, setStock] = useState<StockEntry[]>([]);
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [priority, setPriority] = useState<Priority>("media");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadStock(originId).then((entries) => {
      if (cancelled) return;
      const available = entries.filter((e) => e.quantity - e.reserved > 0);
      setStock(available);
      setItemId(available[0]?.item_id ?? "");
    });
    return () => {
      cancelled = true;
    };
  }, [originId, loadStock]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const qty = Number(quantity);
    if (!Number.isInteger(qty) || qty < 1) return setError("Informe uma quantidade maior que zero.");
    if (!itemId) return setError("Escolha um medicamento ou insumo.");
    if (originId === destId) return setError("Origem e destino precisam ser diferentes.");
    setError(null);
    setBusy(true);
    try {
      await onSubmit({
        origin_id: originId,
        dest_id: destId || null,
        items: [{ item_id: itemId, quantity: qty }],
        priority,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível solicitar. Tente de novo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
      <div>
        <label htmlFor="origin" className={LABEL}>
          Origem
        </label>
        <select id="origin" className={FIELD} value={originId} onChange={(e) => setOriginId(e.target.value)}>
          {origins.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="item" className={LABEL}>
          Medicamento ou insumo
        </label>
        <select id="item" className={FIELD} value={itemId} onChange={(e) => setItemId(e.target.value)}>
          {stock.map((s) => (
            <option key={s.item_id} value={s.item_id}>
              {`${s.item_name} (${s.quantity - s.reserved} disponíveis)`}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="quantity" className={LABEL}>
          Quantidade
        </label>
        <input
          id="quantity"
          type="number"
          inputMode="numeric"
          min={1}
          className={`${FIELD} tabular-nums`}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
      </div>

      <fieldset className="grid gap-2">
        <legend className={LABEL}>Prioridade</legend>
        <div className="grid grid-cols-3 gap-2">
          {PRIORITIES.map((p) => (
            <label
              key={p.value}
              className="flex min-h-controle cursor-pointer items-center justify-center gap-2 rounded-controle border border-neutro-200 bg-branco px-3 text-sm font-medium has-[:checked]:border-azul-500 has-[:checked]:bg-azul-50"
            >
              <input
                type="radio"
                name="priority"
                value={p.value}
                checked={priority === p.value}
                onChange={() => setPriority(p.value)}
                className="accent-azul-500"
              />
              {p.label}
            </label>
          ))}
        </div>
        {priority === "critica" && (
          <p className="text-sm text-vermelho-600">Prioridade crítica exige a assinatura do farmacêutico.</p>
        )}
      </fieldset>

      <div>
        <label htmlFor="dest" className={LABEL}>
          Destino
        </label>
        <select id="dest" className={FIELD} value={destId} onChange={(e) => setDestId(e.target.value)}>
          {places.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
          {error}
        </p>
      )}

      <Button type="submit" size="lg" disabled={busy || !itemId}>
        Solicitar medicamento
      </Button>
    </form>
  );
}
```

`web/src/pages/SolicitarPage.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { DeliveryCreate, Location, Me } from "../api/types";
import { Card } from "../components/Card";
import { RequestForm } from "../components/RequestForm";

export function SolicitarPage() {
  const [data, setData] = useState<{ me: Me; locations: Location[] } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const loadStock = useCallback((originId: string) => api.stock(originId), []);

  useEffect(() => {
    Promise.all([api.me(), api.locations()])
      .then(([me, locations]) => setData({ me, locations }))
      .catch((err: Error) => setLoadError(err.message));
  }, []);

  async function submit(body: DeliveryCreate) {
    await api.createDelivery(body);
    setDone(true);
  }

  if (loadError) return <p role="alert" className="text-vermelho-600">{loadError}</p>;
  if (!data) return <p className="text-neutro-500">Carregando…</p>;

  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Solicitar medicamento</h1>
      <Card className="mt-4">
        <RequestForm locations={data.locations} defaultDestId={data.me.local_id} loadStock={loadStock} onSubmit={submit} />
      </Card>
      {done && (
        <p role="status" className="mt-4 rounded-controle bg-sucesso-50 px-4 py-3 text-sucesso-700">
          Entrega solicitada. Acompanhe em Minhas entregas.
        </p>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `npm test -- --run`
Expected: `34 passed`. Se `getByLabelText("Crítica")` falhar por ambiguidade, confira que só o radio tem esse rótulo (o aviso de prioridade crítica fica em um `<p>`, não em label).

- [ ] **Step 5: Commit**

```bash
cd ..
git add web
git commit -m "feat(web): formulario de solicitar medicamento e SolicitarPage"
```

---

### Task 6: Login, navegação e o app montado

**Files:**
- Create: `web/src/components/AppShell.tsx`, `web/src/pages/LoginPage.tsx`
- Modify: `web/src/App.tsx`, `web/src/App.test.tsx`
- Test: `web/src/components/AppShell.test.tsx`, `web/src/pages/LoginPage.test.tsx`

**Interfaces:**
- Consumes: `api.login`, `setToken`, `Button`, `Card`, `SolicitarPage` (Tarefas 2 a 5).
- Produces:
  - `AppShell({ active, onNavigate, children })` com `PageId = "solicitar" | "entregas" | "estoque"`: barra lateral de ícones (≥ 768 px) e barra inferior (< 768 px), `aria-current="page"` no item ativo.
  - `LoginPage({ onLogin })`.
  - `App` completo: login → `AppShell` com `SolicitarPage`; as outras abas mostram "Em breve." (telas das semanas 2 e 3).

- [ ] **Step 1: Escrever os testes (falham primeiro)**

`web/src/components/AppShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "./AppShell";

test("tem a barra lateral (desktop) e a barra inferior (celular) com os mesmos itens", () => {
  render(
    <AppShell active="solicitar" onNavigate={vi.fn()}>
      <p>conteúdo</p>
    </AppShell>,
  );
  const navs = screen.getAllByRole("navigation");
  expect(navs).toHaveLength(2);
  expect(navs[0]).toHaveClass("hidden", "md:flex");
  expect(navs[1]).toHaveClass("md:hidden");
  expect(screen.getAllByRole("button", { name: "Solicitar" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Minhas entregas" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Estoque" })).toHaveLength(2);
  expect(screen.getByText("conteúdo")).toBeInTheDocument();
});

test("marca a página ativa com aria-current", () => {
  render(
    <AppShell active="entregas" onNavigate={vi.fn()}>
      x
    </AppShell>,
  );
  for (const button of screen.getAllByRole("button", { name: "Minhas entregas" })) {
    expect(button).toHaveAttribute("aria-current", "page");
  }
  for (const button of screen.getAllByRole("button", { name: "Solicitar" })) {
    expect(button).not.toHaveAttribute("aria-current");
  }
});

test("clicar num item navega", async () => {
  const onNavigate = vi.fn();
  render(
    <AppShell active="solicitar" onNavigate={onNavigate}>
      x
    </AppShell>,
  );
  await userEvent.click(screen.getAllByRole("button", { name: "Estoque" })[0]);
  expect(onNavigate).toHaveBeenCalledWith("estoque");
});

test("os botões de navegação têm alvo de toque de 44 px", () => {
  render(
    <AppShell active="solicitar" onNavigate={vi.fn()}>
      x
    </AppShell>,
  );
  for (const button of screen.getAllByRole("button")) expect(button).toHaveClass("min-h-controle");
});
```

`web/src/pages/LoginPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setToken } from "../api/client";
import { LoginPage } from "./LoginPage";

afterEach(() => setToken(null));

test("entra com usuário e senha corretos", async () => {
  const onLogin = vi.fn();
  render(<LoginPage onLogin={onLogin} />);
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await vi.waitFor(() => expect(onLogin).toHaveBeenCalledTimes(1));
});

test("senha errada mostra a mensagem da API e não entra", async () => {
  const onLogin = vi.fn();
  render(<LoginPage onLogin={onLogin} />);
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "errada");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Usuário ou senha incorretos. Tente de novo.");
  expect(onLogin).not.toHaveBeenCalled();
});
```

Replace `web/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { setToken } from "./api/client";

afterEach(() => setToken(null));

test("começa no login, entra e mostra a tela de solicitar", async () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "G.E.R.A.L.D.O." })).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByRole("heading", { name: "Solicitar medicamento" })).toBeInTheDocument();
});

test("as outras abas mostram Em breve", async () => {
  render(<App />);
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByRole("heading", { name: "Solicitar medicamento" });
  await userEvent.click(screen.getAllByRole("button", { name: "Estoque" })[0]);
  expect(screen.getByText("Em breve.")).toBeInTheDocument();
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `npm test -- --run`
Expected: FAIL (componentes novos não existem).

- [ ] **Step 3: Implementar**

`web/src/components/AppShell.tsx`:

```tsx
import { Boxes, PackageCheck, PackagePlus, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type PageId = "solicitar" | "entregas" | "estoque";

const ITEMS: { id: PageId; label: string; Icon: LucideIcon }[] = [
  { id: "solicitar", label: "Solicitar", Icon: PackagePlus },
  { id: "entregas", label: "Minhas entregas", Icon: PackageCheck },
  { id: "estoque", label: "Estoque", Icon: Boxes },
];

interface Props {
  active: PageId;
  onNavigate: (page: PageId) => void;
  children: ReactNode;
}

function NavButton({ id, label, Icon, active, onNavigate, vertical }: (typeof ITEMS)[number] & Omit<Props, "children"> & { vertical: boolean }) {
  const isActive = active === id;
  const color = isActive ? "text-azul-600" : "text-neutro-400";
  return (
    <button
      type="button"
      aria-label={label}
      aria-current={isActive ? "page" : undefined}
      onClick={() => onNavigate(id)}
      className={`flex min-h-controle min-w-controle items-center justify-center rounded-controle ${color} ${vertical ? "w-12" : "flex-1 flex-col gap-0.5 text-xs"} ${isActive ? "bg-azul-50" : ""}`}
    >
      <Icon size={24} aria-hidden="true" />
      {!vertical && <span aria-hidden="true">{label}</span>}
    </button>
  );
}

export function AppShell({ active, onNavigate, children }: Props) {
  return (
    <div className="min-h-screen md:pl-[72px]">
      <nav className="hidden border-r border-neutro-100 bg-branco md:fixed md:inset-y-0 md:left-0 md:flex md:w-[72px] md:flex-col md:items-center md:gap-2 md:pt-6">
        {ITEMS.map((item) => (
          <NavButton key={item.id} {...item} active={active} onNavigate={onNavigate} vertical />
        ))}
      </nav>
      <main className="mx-auto max-w-[1280px] px-4 pb-24 pt-4 md:px-6 md:pb-6">{children}</main>
      <nav className="fixed inset-x-0 bottom-0 flex border-t border-neutro-100 bg-branco px-2 py-1 md:hidden">
        {ITEMS.map((item) => (
          <NavButton key={item.id} {...item} active={active} onNavigate={onNavigate} vertical={false} />
        ))}
      </nav>
    </div>
  );
}
```


`web/src/pages/LoginPage.tsx`:

```tsx
import { useState, type FormEvent } from "react";
import { api, setToken } from "../api/client";
import { Button } from "../components/Button";
import { Card } from "../components/Card";

const FIELD =
  "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 text-base text-tinta " +
  "focus:border-azul-500 focus:outline-none focus:ring-2 focus:ring-azul-200";

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { access_token } = await api.login(username, password);
      setToken(access_token);
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível entrar. Tente de novo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-screen max-w-sm content-center gap-6 px-4">
      <h1 className="text-center font-display text-3xl font-bold text-azul-600">G.E.R.A.L.D.O.</h1>
      <Card>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium text-neutro-700">
              Usuário
            </label>
            <input id="username" className={FIELD} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-neutro-700">
              Senha
            </label>
            <input id="password" type="password" className={FIELD} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          {error && (
            <p role="alert" className="rounded-controle border border-vermelho-200 bg-vermelho-50 px-3 py-2 text-sm text-vermelho-600">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={busy}>
            Entrar
          </Button>
        </form>
      </Card>
    </main>
  );
}
```

Replace `web/src/App.tsx`:

```tsx
import { useState } from "react";
import { AppShell, type PageId } from "./components/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { SolicitarPage } from "./pages/SolicitarPage";

export default function App() {
  const [logged, setLogged] = useState(false);
  const [page, setPage] = useState<PageId>("solicitar");

  if (!logged) return <LoginPage onLogin={() => setLogged(true)} />;
  return (
    <AppShell active={page} onNavigate={setPage}>
      {page === "solicitar" ? <SolicitarPage /> : <p className="text-neutro-500">Em breve.</p>}
    </AppShell>
  );
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `npm test -- --run && npm run build`
Expected: `41 passed` e o build termina sem erro de tipos (o `tsc` também confere as opções do MSW).

- [ ] **Step 5: Ver no navegador (celular e desktop)**

Com o backend do Erik rodando (`GERALDO_DEMO_PASSWORD` definido) e o app em `npm run dev`, entre com `medico1` e a senha de demonstração. Abra as ferramentas do navegador, ative o modo de dispositivo (largura de 375 px) e confira: barra inferior com 3 ícones, formulário em uma coluna, botões com pelo menos 44 px de altura. Em 1024 px ou mais, a barra lateral de ícones aparece e a inferior some.

- [ ] **Step 6: Commit e PR**

```bash
cd ..
git add web
git commit -m "feat(web): login, navegacao responsiva e app montado"
```

---

### Task 7: Tela "Minhas entregas" e `DeliveryQueueRow`

**Files:**
- Create: `web/src/components/DeliveryQueueRow.tsx`, `web/src/pages/MinhasEntregasPage.tsx`
- Modify: `web/src/api/mocks/fixtures.ts` (acrescenta `DELIVERY`), `web/src/App.tsx`
- Test: `web/src/components/DeliveryQueueRow.test.tsx`, `web/src/pages/MinhasEntregasPage.test.tsx`; acrescenta um teste em `web/src/App.test.tsx`

**Interfaces:**
- Consumes: `api.deliveries()`, `api.locations()`, `PriorityBadge`, `StatusBadge`, `Button`, `Card` (Tarefas 2 a 5).
- Produces:
  - `DeliveryQueueRow({ delivery, locationName })`: linha arredondada com horário (fuso de São Paulo), itens, `origem → destino`, e os selos de prioridade e status (no celular os selos descem para a segunda linha).
  - `MinhasEntregasPage({ onRequest })`: lista as entregas do usuário; sem entregas, mostra o estado vazio com o botão "Solicitar medicamento" que chama `onRequest`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Acrescente ao final de `web/src/api/mocks/fixtures.ts`:

```ts
import type { Delivery } from "../types";

export const DELIVERY: Delivery = {
  id: 1,
  origin_id: "farmacia",
  dest_id: "consultorio1",
  items: [{ item_id: "dipirona-500mg", quantity: 5 }],
  priority: "media",
  status: "EM_ROTA",
  requested_by: 1,
  created_at: "2026-11-09T13:20:00Z",
};
```

(Junte o `import type { Delivery }` ao import existente do topo do arquivo, para ficar um só.)

`web/src/components/DeliveryQueueRow.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { DELIVERY, LOCATIONS } from "../api/mocks/fixtures";
import { DeliveryQueueRow } from "./DeliveryQueueRow";

const name = (id: string) => LOCATIONS.find((l) => l.id === id)?.name ?? id;

test("mostra horário, itens, origem e destino, prioridade e status", () => {
  render(
    <ul>
      <DeliveryQueueRow delivery={DELIVERY} locationName={name} />
    </ul>,
  );
  expect(screen.getByText("10:20")).toHaveClass("tabular-nums");
  expect(screen.getByText(/5 × Dipirona 500mg/)).toHaveTextContent("Farmácia central → Consultório 1");
  expect(screen.getByText("Média")).toBeInTheDocument();
  expect(screen.getByText("A caminho")).toBeInTheDocument();
});

test("é uma linha arredondada de fundo claro que quebra em duas linhas no celular", () => {
  render(
    <ul>
      <DeliveryQueueRow delivery={DELIVERY} locationName={name} />
    </ul>,
  );
  expect(screen.getByRole("listitem")).toHaveClass("rounded-controle", "bg-fundo", "flex-col", "md:flex-row");
});
```

`web/src/pages/MinhasEntregasPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setToken } from "../api/client";
import { DELIVERY } from "../api/mocks/fixtures";
import { server } from "../api/mocks/server";
import { MinhasEntregasPage } from "./MinhasEntregasPage";

afterEach(() => setToken(null));

test("lista as entregas do usuário com os nomes dos locais", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json([DELIVERY])));
  render(<MinhasEntregasPage onRequest={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
  expect(await screen.findByText(/Farmácia central → Consultório 1/)).toBeInTheDocument();
  expect(screen.getByText("A caminho")).toBeInTheDocument();
});

test("sem entregas mostra o estado vazio e leva para o formulário", async () => {
  const onRequest = vi.fn();
  render(<MinhasEntregasPage onRequest={onRequest} />);
  expect(await screen.findByText("Nenhuma entrega ainda")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(onRequest).toHaveBeenCalledTimes(1);
});

test("erro da API aparece como alerta", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
  render(<MinhasEntregasPage onRequest={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Faça login para continuar.");
});
```

Acrescente ao final de `web/src/App.test.tsx`:

```tsx
test("a aba Minhas entregas mostra a lista", async () => {
  render(<App />);
  await userEvent.type(screen.getByLabelText("Usuário"), "medico1");
  await userEvent.type(screen.getByLabelText("Senha"), "demo");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByRole("heading", { name: "Solicitar medicamento" });
  await userEvent.click(screen.getAllByRole("button", { name: "Minhas entregas" })[0]);
  expect(await screen.findByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run (em `web/`): `npm test -- --run`
Expected: FAIL (componente e página não existem).

- [ ] **Step 3: Implementar**

`web/src/components/DeliveryQueueRow.tsx`:

```tsx
import type { Delivery } from "../api/types";
import { PriorityBadge } from "./PriorityBadge";
import { StatusBadge } from "./StatusBadge";

// O contrato devolve só o id do item (ex.: "dipirona-500mg"); mostramos uma versão legível dele.
const humanize = (id: string) => {
  const text = id.replace(/-/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });

interface Props {
  delivery: Delivery;
  locationName: (id: string) => string;
}

export function DeliveryQueueRow({ delivery, locationName }: Props) {
  const items = delivery.items.map((i) => `${i.quantity} × ${humanize(i.item_id)}`).join(", ");
  return (
    <li className="flex flex-col gap-2 rounded-controle bg-fundo px-3 py-3 md:flex-row md:items-center md:gap-3">
      <span className="w-12 text-xs tabular-nums text-neutro-500">{clock(delivery.created_at)}</span>
      <span className="flex-1 text-sm">
        {items} · {locationName(delivery.origin_id)} → {locationName(delivery.dest_id)}
      </span>
      <span className="flex flex-wrap gap-2">
        <PriorityBadge priority={delivery.priority} />
        <StatusBadge status={delivery.status} />
      </span>
    </li>
  );
}
```

`web/src/pages/MinhasEntregasPage.tsx`:

```tsx
import { PackageCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Delivery, Location } from "../api/types";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";

export function MinhasEntregasPage({ onRequest }: { onRequest: () => void }) {
  const [data, setData] = useState<{ deliveries: Delivery[]; locations: Location[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.deliveries(), api.locations()])
      .then(([deliveries, locations]) => setData({ deliveries, locations }))
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <p role="alert" className="text-vermelho-600">{error}</p>;
  if (!data) return <p className="text-neutro-500">Carregando…</p>;

  const locationName = (id: string) => data.locations.find((l) => l.id === id)?.name ?? id;

  return (
    <section>
      <h1 className="font-display text-2xl font-bold">Minhas entregas</h1>
      <Card className="mt-4">
        {data.deliveries.length === 0 ? (
          <div className="grid justify-items-center gap-3 py-6 text-center">
            <PackageCheck size={40} aria-hidden="true" className="text-neutro-300" />
            <p className="font-display text-lg font-semibold">Nenhuma entrega ainda</p>
            <p className="text-sm text-neutro-500">Solicite um medicamento para acompanhar a entrega aqui.</p>
            <Button onClick={onRequest}>Solicitar medicamento</Button>
          </div>
        ) : (
          <ul className="grid gap-2">
            {data.deliveries.map((d) => (
              <DeliveryQueueRow key={d.id} delivery={d} locationName={locationName} />
            ))}
          </ul>
        )}
      </Card>
    </section>
  );
}
```

Replace `web/src/App.tsx`:

```tsx
import { useState } from "react";
import { AppShell, type PageId } from "./components/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { MinhasEntregasPage } from "./pages/MinhasEntregasPage";
import { SolicitarPage } from "./pages/SolicitarPage";

export default function App() {
  const [logged, setLogged] = useState(false);
  const [page, setPage] = useState<PageId>("solicitar");

  if (!logged) return <LoginPage onLogin={() => setLogged(true)} />;
  return (
    <AppShell active={page} onNavigate={setPage}>
      {page === "solicitar" && <SolicitarPage />}
      {page === "entregas" && <MinhasEntregasPage onRequest={() => setPage("solicitar")} />}
      {page === "estoque" && <p className="text-neutro-500">Em breve.</p>}
    </AppShell>
  );
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `npm test -- --run && npm run build`
Expected: `47 passed` e o build termina sem erro de tipos.

- [ ] **Step 5: Commit e PR**

```bash
cd ..
git add web
git commit -m "feat(web): tela Minhas entregas e DeliveryQueueRow"
git push -u origin HEAD
```

Abra o PR e avise o Samuel: tokens e componentes prontos; a semana 2 traz a confirmação de recebimento e o painel de estoque, fila e histórico.
