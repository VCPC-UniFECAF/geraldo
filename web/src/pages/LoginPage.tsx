import { useState, type FormEvent } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { Sessao } from "../domain/Sessao";

const FIELD =
  "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 text-base text-tinta " +
  "focus:border-azul-500 focus:outline-none focus:ring-2 focus:ring-azul-200";

export function LoginPage({ sessao }: { sessao: Sessao }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await sessao.entrar(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível entrar. Tente de novo.");
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
