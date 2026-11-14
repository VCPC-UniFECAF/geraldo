import { render, screen } from "@testing-library/react";
import { TELEMETRIAS } from "../api/mocks/fixtures";
import { TelemetryPanel } from "./TelemetryPanel";

test("desenha o mapa com a rota e mostra posição e direção em tabular-nums", () => {
  const { container } = render(<TelemetryPanel telemetria={TELEMETRIAS.A_CAMINHO} />);
  expect(screen.getByRole("img", { name: "Mapa simples com o robô, a rota e os obstáculos" })).toBeInTheDocument();
  expect(container.querySelectorAll("polyline")).toHaveLength(1);
  expect(screen.getByText("x 14,2 m · y 28,9 m")).toHaveClass("tabular-nums");
  expect(screen.getByText("0°")).toBeInTheDocument();
  expect(screen.getByText("1 obstáculo")).toBeInTheDocument();
});

test("desenha um círculo de aviso (não vermelho) por obstáculo e conta no singular e no plural", () => {
  const dois = { ...TELEMETRIAS.A_CAMINHO, obstacles: [{ x: 18, y: 28.9, radius: 0.4 }, { x: 22, y: 28.5, radius: 0.5 }] };
  const { container, rerender } = render(<TelemetryPanel telemetria={dois} />);
  expect(container.querySelectorAll("circle[data-obstaculo]")).toHaveLength(2);
  expect(container.querySelector("circle[data-obstaculo]")).toHaveClass("stroke-aviso-500");
  expect(screen.getByText("2 obstáculos")).toBeInTheDocument();
  rerender(<TelemetryPanel telemetria={{ ...dois, obstacles: [dois.obstacles[0]] }} />);
  expect(screen.getByText("1 obstáculo")).toBeInTheDocument();
});

test("sem telemetria mostra o texto de espera e não desenha o mapa", () => {
  render(<TelemetryPanel telemetria={null} />);
  expect(screen.getByText("Sem dados do robô ainda.")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
