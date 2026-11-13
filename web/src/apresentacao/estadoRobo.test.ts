import { ROBOT_STATES } from "../api/types";
import { estadoRoboDe } from "./estadoRobo";

test("todo estado do contrato tem apresentação", () => {
  for (const estado of ROBOT_STATES) expect(estadoRoboDe(estado).valor).toBe(estado);
});

test("só a parada de emergência é vermelha e marcada como emergência", () => {
  expect(estadoRoboDe("PARADA_EMERGENCIA").emEmergencia).toBe(true);
  expect(estadoRoboDe("PARADA_EMERGENCIA").caixa).toContain("vermelho");
  for (const estado of ROBOT_STATES.filter((e) => e !== "PARADA_EMERGENCIA")) {
    expect(estadoRoboDe(estado).emEmergencia).toBe(false);
    expect(estadoRoboDe(estado).caixa).not.toContain("vermelho");
  }
});

test("rótulos em português", () => {
  expect(estadoRoboDe("IDLE").rotulo).toBe("Livre");
  expect(estadoRoboDe("A_CAMINHO").rotulo).toBe("A caminho");
  expect(estadoRoboDe("AGUARDANDO_RETIRADA").rotulo).toBe("Aguardando retirada");
  expect(estadoRoboDe("PARADA_EMERGENCIA").rotulo).toBe("Parada de emergência");
});
