// Datas e horas da interface sempre no fuso de São Paulo, qualquer que seja o fuso do navegador.
const FUSO = "America/Sao_Paulo";

export const horario = (data: Date): string =>
  data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: FUSO });

export const dataCurta = (data: Date): string =>
  data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", timeZone: FUSO });
