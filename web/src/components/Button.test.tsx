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
