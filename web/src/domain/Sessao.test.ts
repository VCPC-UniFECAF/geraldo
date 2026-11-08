import { ApiError } from "../api/ApiClient";
import type { SessaoApi } from "../api/ApiClient";
import { Sessao, TokenObserver } from "./Sessao";

function apiFalsa(login: SessaoApi["login"]) {
  const tokens: (string | null)[] = [];
  const api: SessaoApi = { login, me: vi.fn(), definirToken: (t) => tokens.push(t) };
  return { api, tokens };
}

test("entrar faz login e notifica os observers com o token", async () => {
  const { api } = apiFalsa(async () => ({ access_token: "abc", token_type: "bearer" }));
  const sessao = new Sessao(api);
  const eventos: unknown[] = [];
  sessao.adicionarObserver({ atualizar: (e) => eventos.push(e) });
  await sessao.entrar("medico1", "demo");
  expect(eventos).toEqual([{ tipo: "entrou", token: "abc" }]);
});

test("o TokenObserver guarda o token no cliente da API antes dos observers seguintes", async () => {
  const { api, tokens } = apiFalsa(async () => ({ access_token: "abc", token_type: "bearer" }));
  const sessao = new Sessao(api);
  let tokenQuandoAvisou: (string | null) | undefined;
  sessao.adicionarObserver(new TokenObserver(api));
  sessao.adicionarObserver({ atualizar: () => (tokenQuandoAvisou = tokens[tokens.length - 1]) });
  await sessao.entrar("medico1", "demo");
  expect(tokenQuandoAvisou).toBe("abc");
});

test("login recusado propaga o erro e não notifica ninguém", async () => {
  const { api } = apiFalsa(async () => {
    throw new ApiError(401, "Usuário ou senha incorretos. Tente de novo.");
  });
  const sessao = new Sessao(api);
  const atualizar = vi.fn();
  sessao.adicionarObserver({ atualizar });
  await expect(sessao.entrar("medico1", "errada")).rejects.toMatchObject({ status: 401 });
  expect(atualizar).not.toHaveBeenCalled();
});
