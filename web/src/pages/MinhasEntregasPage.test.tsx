import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { ADMIN, DELIVERY, DELIVERY_AGUARDANDO, FARMACEUTICO, ME } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { server } from "../api/mocks/server";
import { MinhasEntregasPage } from "./MinhasEntregasPage";

test("lista as entregas do usuário com os nomes dos locais", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json([DELIVERY])));
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
  expect(await screen.findByText(/Farmácia central → Consultório 1/)).toBeInTheDocument();
  expect(screen.getByText("A caminho")).toBeInTheDocument();
});

test("sem entregas mostra o estado vazio e leva para o formulário", async () => {
  const onRequest = vi.fn();
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={onRequest} />);
  expect(await screen.findByText("Nenhuma entrega ainda")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Solicitar medicamento" }));
  expect(onRequest).toHaveBeenCalledTimes(1);
});

test("erro da API na primeira carga aparece como alerta", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Erro no servidor. Tente de novo." }, { status: 500 })));
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Erro no servidor. Tente de novo.");
});

test("401 na primeira carga leva à sessão expirada, como o Painel", async () => {
  server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Sua sessão expirou. Entre de novo para ver suas entregas.");
});

test("erro numa recarga automática aparece sem apagar a lista e some quando a próxima dá certo", async () => {
  semearEntregas([DELIVERY]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} intervaloMs={5000} onRequest={vi.fn()} />);
    expect(await screen.findByText("A caminho")).toBeInTheDocument();
    server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Erro no servidor. Tente de novo." }, { status: 500 }), { once: true }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível atualizar a lista. Erro no servidor. Tente de novo.");
    expect(screen.getByText("A caminho")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  } finally {
    vi.useRealTimers();
  }
});

test("401 numa recarga automática mostra a sessão expirada, mantém a lista e para de recarregar", async () => {
  let chamadas = 0;
  semearEntregas([DELIVERY]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} intervaloMs={5000} onRequest={vi.fn()} />);
    expect(await screen.findByText("A caminho")).toBeInTheDocument();
    server.use(
      http.get("http://localhost:8000/deliveries", () => {
        chamadas += 1;
        return HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 });
      }),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Sua sessão expirou. Entre de novo para ver suas entregas.");
    expect(screen.getByText("A caminho")).toBeInTheDocument();
    const antes = chamadas;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20000);
    });
    expect(chamadas).toBe(antes);
  } finally {
    vi.useRealTimers();
  }
});

test("só a entrega aguardando recebimento tem o botão Confirmar recebimento", async () => {
  semearEntregas([DELIVERY, DELIVERY_AGUARDANDO]);
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  expect(await screen.findAllByRole("listitem")).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: /Confirmar recebimento/ })).toHaveLength(1);
});

test("confirmar o recebimento mostra o aviso e a entrega vira Entregue", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: /Confirmar recebimento/ }));
  expect(await screen.findByRole("status")).toHaveTextContent("Recebimento confirmado. A tampa do robô foi liberada.");
  expect(await screen.findByText("Entregue")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Confirmar recebimento/ })).not.toBeInTheDocument();
});

test("erro ao confirmar aparece como alerta e a lista continua na tela", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  server.use(
    http.post("http://localhost:8000/deliveries/2/confirm-receipt", () =>
      HttpResponse.json({ detail: "Só quem solicitou a entrega confirma o recebimento." }, { status: 403 }),
    ),
  );
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: /Confirmar recebimento/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Só quem solicitou a entrega confirma o recebimento.");
  expect(screen.getByRole("button", { name: /Confirmar recebimento/ })).toBeEnabled();
});

test("se o recarregamento falhar depois de confirmar, mostra o sucesso e o erro da lista à parte", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  let chamadas = 0;
  server.use(
    http.get("http://localhost:8000/deliveries", () => {
      chamadas += 1;
      return chamadas === 1
        ? HttpResponse.json([DELIVERY_AGUARDANDO])
        : HttpResponse.json({ detail: "Não foi possível carregar as entregas." }, { status: 500 });
    }),
  );
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: /Confirmar recebimento/ }));
  expect(await screen.findByRole("status")).toHaveTextContent("Recebimento confirmado.");
  expect(await screen.findByRole("alert")).toHaveTextContent("Recebimento confirmado, mas a lista não atualizou");
  expect(screen.getByRole("heading", { name: "Minhas entregas" })).toBeInTheDocument();
});

test("enquanto uma confirmação está em andamento todos os botões ficam desabilitados", async () => {
  semearEntregas([DELIVERY_AGUARDANDO, { ...DELIVERY_AGUARDANDO, id: 5 }]);
  let liberar: () => void = () => {};
  const portao = new Promise<void>((r) => (liberar = r));
  server.use(
    http.post("http://localhost:8000/deliveries/:id/confirm-receipt", async () => {
      await portao;
      return HttpResponse.json({});
    }),
  );
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  const botoes = await screen.findAllByRole("button", { name: /Confirmar recebimento/ });
  await userEvent.click(botoes[0]);
  for (const b of screen.getAllByRole("button", { name: /Confirmar recebimento/ })) expect(b).toBeDisabled();
  liberar();
});

test("farmacêutico não vê o botão numa entrega pedida por outra pessoa", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={FARMACEUTICO} onRequest={vi.fn()} />);
  expect(await screen.findAllByRole("listitem")).toHaveLength(1);
  expect(screen.queryByRole("button", { name: /Confirmar recebimento/ })).not.toBeInTheDocument();
});

test("farmacêutico vê o botão na entrega que ele mesmo pediu, e o admin em qualquer uma", async () => {
  semearEntregas([{ ...DELIVERY_AGUARDANDO, requested_by: FARMACEUTICO.id }]);
  const { unmount } = render(<MinhasEntregasPage api={new HttpApiClient()} usuario={FARMACEUTICO} onRequest={vi.fn()} />);
  expect(await screen.findByRole("button", { name: /Confirmar recebimento/ })).toBeInTheDocument();
  unmount();
  semearEntregas([DELIVERY_AGUARDANDO]);
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ADMIN} onRequest={vi.fn()} />);
  expect(await screen.findByRole("button", { name: /Confirmar recebimento/ })).toBeInTheDocument();
});

test("recarrega a lista sozinha: o robô chega e o botão aparece sem trocar de aba", async () => {
  semearEntregas([DELIVERY]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} intervaloMs={5000} onRequest={vi.fn()} />);
    expect(await screen.findByText("A caminho")).toBeInTheDocument();
    semearEntregas([DELIVERY_AGUARDANDO]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(await screen.findByRole("button", { name: /Confirmar recebimento/ })).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test("ao desmontar para de recarregar a lista", async () => {
  let chamadas = 0;
  server.use(
    http.get("http://localhost:8000/deliveries", () => {
      chamadas += 1;
      return HttpResponse.json([DELIVERY]);
    }),
  );
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    const { unmount } = render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} intervaloMs={5000} onRequest={vi.fn()} />);
    await screen.findByText("A caminho");
    unmount();
    const antes = chamadas;
    await vi.advanceTimersByTimeAsync(20000);
    expect(chamadas).toBe(antes);
  } finally {
    vi.useRealTimers();
  }
});

test("quando a sessão expira, o aviso de erro de recarga anterior some (só fica a sessão expirada)", async () => {
  semearEntregas([DELIVERY]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} intervaloMs={5000} onRequest={vi.fn()} />);
    expect(await screen.findByText("A caminho")).toBeInTheDocument();
    server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Erro no servidor. Tente de novo." }, { status: 500 }), { once: true }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível atualizar a lista.");
    server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await waitFor(() => expect(screen.getByText(/Sua sessão expirou/)).toBeInTheDocument());
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  } finally {
    vi.useRealTimers();
  }
});
