import { render, screen } from "@testing-library/react";
import { STOCK } from "../api/mocks/fixtures";
import { StockLevelBar } from "./StockLevelBar";

const [dipirona, , sangue] = STOCK;

function mostrar(entrada = dipirona, local = "Farmácia central") {
  return render(
    <ul>
      <StockLevelBar entrada={entrada} local={local} />
    </ul>,
  );
}

test("mostra item, local, quantidade em tabular-nums e a barra cheia quando o saldo é folgado", () => {
  mostrar();
  expect(screen.getByText("Dipirona 500 mg")).toBeInTheDocument();
  expect(screen.getByText("Farmácia central")).toBeInTheDocument();
  expect(screen.getByText("420")).toHaveClass("tabular-nums");
  const barra = screen.getByRole("progressbar", { name: "Nível de Dipirona 500 mg" });
  expect(barra).toHaveAttribute("aria-valuenow", "420");
  expect(barra.firstElementChild).toHaveClass("bg-azul-500");
  expect(barra.firstElementChild).toHaveStyle({ width: "100%" });
  expect(screen.queryByText("Abaixo do mínimo")).not.toBeInTheDocument();
});

test("abaixo do mínimo fica vermelho e diz Abaixo do mínimo", () => {
  mostrar(sangue, "Banco de sangue");
  const barra = screen.getByRole("progressbar", { name: "Nível de Bolsa de sangue O negativo" });
  expect(barra.firstElementChild).toHaveClass("bg-vermelho-500");
  expect(barra.firstElementChild).toHaveStyle({ width: "30%" });
  expect(screen.getByText("Abaixo do mínimo")).toBeInTheDocument();
  expect(screen.getByText(/Mínimo 10 · reservado 0/)).toHaveClass("tabular-nums");
});

test("perto do mínimo usa aviso e o texto Perto do mínimo", () => {
  mostrar({ ...dipirona, quantity: 110 });
  expect(screen.getByText("Perto do mínimo")).toBeInTheDocument();
  expect(screen.getByRole("progressbar").firstElementChild).toHaveClass("bg-aviso-500");
});
