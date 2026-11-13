import { render, screen, within } from "@testing-library/react";
import { TELEMETRIAS } from "../api/mocks/fixtures";
import { RobotStatusCard } from "./RobotStatusCard";

test("mostra o nome, o estado, a entrega em curso, a chegada estimada e a bateria", () => {
  render(<RobotStatusCard telemetria={TELEMETRIAS.A_CAMINHO} entrega="Entrega #7 · Consultório 1" />);
  const cartao = screen.getByRole("region", { name: "Estado do robô" });
  expect(within(cartao).getByRole("heading", { name: "G.E.R.A.L.D.O." })).toBeInTheDocument();
  expect(within(cartao).getByText("A caminho")).toBeInTheDocument();
  expect(within(cartao).getByText("Entrega #7 · Consultório 1")).toBeInTheDocument();
  expect(within(cartao).getByText("Cerca de 5 s")).toBeInTheDocument();
  expect(within(cartao).getByText("99%")).toHaveClass("tabular-nums");
  const bateria = within(cartao).getByRole("progressbar", { name: "Bateria" });
  expect(bateria).toHaveAttribute("aria-valuenow", "99");
  expect(bateria.firstElementChild).toHaveClass("bg-azul-500");
});

test("sem entrega e sem rota mostra os textos de espera", () => {
  render(<RobotStatusCard telemetria={TELEMETRIAS.IDLE} entrega={null} />);
  expect(screen.getByText("Sem entrega em curso")).toBeInTheDocument();
  expect(screen.getByText("—")).toBeInTheDocument();
  expect(screen.getByText("Livre")).toBeInTheDocument();
});

test("bateria abaixo de 20% fica vermelha e diz Bateria baixa", () => {
  render(<RobotStatusCard telemetria={{ ...TELEMETRIAS.IDLE, battery: 15 }} entrega={null} />);
  expect(screen.getByText("Bateria baixa")).toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "Bateria" }).firstElementChild).toHaveClass("bg-vermelho-500");
});

test("parada de emergência aparece em vermelho com o texto", () => {
  render(<RobotStatusCard telemetria={TELEMETRIAS.PARADA_EMERGENCIA} entrega={null} />);
  expect(screen.getByText("Parada de emergência").closest("span")).toHaveClass("bg-vermelho-100");
});

test("sem telemetria diz que não há sinal", () => {
  render(<RobotStatusCard telemetria={null} entrega={null} />);
  expect(screen.getByText("Sem sinal do robô. Confira se a simulação está ligada.")).toBeInTheDocument();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});

test("a barra de bateria fica entre 0 e 100", () => {
  const { rerender } = render(<RobotStatusCard telemetria={{ ...TELEMETRIAS.IDLE, battery: 130 }} entrega={null} />);
  expect(screen.getByRole("progressbar", { name: "Bateria" }).firstElementChild).toHaveStyle({ width: "100%" });
  rerender(<RobotStatusCard telemetria={{ ...TELEMETRIAS.IDLE, battery: -5 }} entrega={null} />);
  expect(screen.getByRole("progressbar", { name: "Bateria" }).firstElementChild).toHaveStyle({ width: "0%" });
});
