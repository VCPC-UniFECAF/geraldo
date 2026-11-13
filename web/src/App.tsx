import { useEffect, useMemo, useState } from "react";
import type { ApiClient } from "./api/ApiClient";
import { HttpApiClient } from "./api/HttpApiClient";
import { AppShell, type PageId } from "./components/AppShell";
import { Sessao, TokenObserver } from "./domain/Sessao";
import { LoginPage } from "./pages/LoginPage";
import { EstoquePage } from "./pages/EstoquePage";
import { MinhasEntregasPage } from "./pages/MinhasEntregasPage";
import { SolicitarPage } from "./pages/SolicitarPage";

// DIP: quem monta o app escolhe a implementação da API; as telas só conhecem as interfaces.
export default function App({ api }: { api?: ApiClient }) {
  const cliente = useMemo<ApiClient>(() => api ?? new HttpApiClient(), [api]);
  const sessao = useMemo(() => {
    const s = new Sessao(cliente);
    s.adicionarObserver(new TokenObserver(cliente)); // primeiro o token, depois a tela
    return s;
  }, [cliente]);
  const [logado, setLogado] = useState(false);
  const [page, setPage] = useState<PageId>("solicitar");

  useEffect(() => {
    const observer = { atualizar: () => setLogado(true) };
    sessao.adicionarObserver(observer);
    return () => sessao.removerObserver(observer);
  }, [sessao]);

  if (!logado) return <LoginPage sessao={sessao} />;
  return (
    <AppShell active={page} onNavigate={setPage}>
      {page === "solicitar" && <SolicitarPage api={cliente} />}
      {page === "entregas" && <MinhasEntregasPage api={cliente} onRequest={() => setPage("solicitar")} />}
      {page === "estoque" && <EstoquePage api={cliente} />}
    </AppShell>
  );
}
