import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import html from "../index.html?raw";
import { HttpApiClient } from "./api/HttpApiClient";
import { DELIVERY_AGUARDANDO } from "./api/mocks/fixtures";
import { semearEntregas } from "./api/mocks/handlers";
import { AppShell } from "./components/AppShell";
import { TelemetriaCliente } from "./domain/TelemetriaCliente";
import { EstoquePage } from "./pages/EstoquePage";
import { MinhasEntregasPage } from "./pages/MinhasEntregasPage";
import { PainelPage } from "./pages/PainelPage";
import { SolicitarPage } from "./pages/SolicitarPage";
import { fabricaDeSockets } from "./test/SocketFalso";

// Alvo de toque mínimo de 44 px: botão, select e campo precisam de min-h-controle (ou do tamanho lg, 52 px). Radios ficam dentro de um label que tem a altura.
const ALVOS = 'button, select, input:not([type="radio"]):not([type="checkbox"])';

function conferirAlvos(container: HTMLElement) {
  const alvos = [...container.querySelectorAll<HTMLElement>(ALVOS)];
  expect(alvos.length).toBeGreaterThan(0);
  for (const alvo of alvos) expect(alvo.className, alvo.outerHTML).toMatch(/min-h-(controle|\[52px\])/);
}

test("o index.html declara o viewport do celular", () => {
  expect(html).toContain('<meta name="viewport" content="width=device-width, initial-scale=1" />');
});

test("Solicitar: todos os controles têm 44 px", async () => {
  const { container } = render(<SolicitarPage api={new HttpApiClient()} />);
  await screen.findByRole("option", { name: /Dipirona/ });
  conferirAlvos(container);
});

test("Minhas entregas: o botão de confirmar recebimento tem 44 px e ocupa a largura no celular", async () => {
  semearEntregas([DELIVERY_AGUARDANDO]);
  const { container } = render(<MinhasEntregasPage api={new HttpApiClient()} onRequest={vi.fn()} />);
  const botao = await screen.findByRole("button", { name: /Confirmar recebimento/ });
  expect(botao).toHaveClass("w-full", "md:w-auto");
  conferirAlvos(container);
});

test("Estoque: filtro e abas têm 44 px nas duas abas", async () => {
  const { container } = render(<EstoquePage api={new HttpApiClient()} />);
  await screen.findByText("Bolsa de sangue O negativo");
  conferirAlvos(container);
  await userEvent.click(screen.getByRole("tab", { name: "Histórico" }));
  await screen.findAllByRole("listitem");
  conferirAlvos(container);
});

test("Painel: o botão de emergência tem 52 px e ocupa a largura no celular", async () => {
  const { criar } = fabricaDeSockets();
  const { container } = render(
    <PainelPage api={new HttpApiClient()} telemetria={new TelemetriaCliente(() => "ws://teste", criar)} role="admin" />,
  );
  const botao = await screen.findByRole("button", { name: "Parada de emergência" });
  expect(botao).toHaveClass("w-full", "md:w-auto");
  await screen.findByText("Livre");
  conferirAlvos(container);
});

test("a navegação (lateral e inferior) tem 44 px e a barra inferior só aparece no celular", () => {
  const { container } = render(
    <AppShell active="painel" onNavigate={vi.fn()}>
      x
    </AppShell>,
  );
  conferirAlvos(container);
  expect(screen.getAllByRole("navigation")[1]).toHaveClass("md:hidden");
});
