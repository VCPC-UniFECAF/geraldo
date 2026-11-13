import { useEffect, useMemo, useState } from "react";
import type { ApiClient } from "./api/ApiClient";
import { HttpApiClient } from "./api/HttpApiClient";
import type { Me } from "./api/types";
import { AppShell, type PageId } from "./components/AppShell";
import { Sessao, TokenObserver } from "./domain/Sessao";
import { TelemetriaCliente } from "./domain/TelemetriaCliente";
import { EstoquePage } from "./pages/EstoquePage";
import { LoginPage } from "./pages/LoginPage";
import { MinhasEntregasPage } from "./pages/MinhasEntregasPage";
import { PainelPage } from "./pages/PainelPage";
import { SolicitarPage } from "./pages/SolicitarPage";

// DIP: quem monta o app escolhe a implementação da API e do cliente de telemetria; as telas só conhecem as interfaces.
export default function App({ api, telemetria }: { api?: ApiClient; telemetria?: TelemetriaCliente }) {
  const cliente = useMemo<ApiClient>(() => api ?? new HttpApiClient(), [api]);
  const stream = useMemo(() => telemetria ?? new TelemetriaCliente(() => cliente.telemetryStreamUrl()), [telemetria, cliente]);
  const sessao = useMemo(() => {
    const s = new Sessao(cliente);
    s.adicionarObserver(new TokenObserver(cliente)); // primeiro o token, depois a tela
    return s;
  }, [cliente]);
  const [logado, setLogado] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [erroMe, setErroMe] = useState<string | null>(null);
  const [page, setPage] = useState<PageId>("solicitar");

  useEffect(() => {
    const observer = { atualizar: () => setLogado(true) };
    sessao.adicionarObserver(observer);
    return () => sessao.removerObserver(observer);
  }, [sessao]);

  // GET /me: o papel decide o que aparece (botão de emergência).
  useEffect(() => {
    if (!logado) return;
    cliente.me().then(setMe).catch((err: Error) => setErroMe(err.message));
  }, [logado, cliente]);

  if (!logado) return <LoginPage sessao={sessao} />;
  if (erroMe) return <p role="alert" className="p-4 text-vermelho-600">{erroMe}</p>;
  if (!me) return <p className="p-4 text-neutro-500">Carregando…</p>;
  return (
    <AppShell active={page} onNavigate={setPage}>
      {page === "solicitar" && <SolicitarPage api={cliente} />}
      {page === "entregas" && <MinhasEntregasPage api={cliente} onRequest={() => setPage("solicitar")} />}
      {page === "estoque" && <EstoquePage api={cliente} />}
      {page === "painel" && <PainelPage api={cliente} telemetria={stream} role={me.role} />}
    </AppShell>
  );
}
