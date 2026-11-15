// Contrato: motivo da recusa de 3 a 200 caracteres, sem espaços nas pontas (a tela tira os espaços antes de enviar).
export const MOTIVO_MIN = 3;
export const MOTIVO_MAX = 200;

export function validarMotivo(texto: string): string | null {
  const tamanho = texto.trim().length;
  return tamanho >= MOTIVO_MIN && tamanho <= MOTIVO_MAX ? null : `Escreva o motivo da recusa com ${MOTIVO_MIN} a ${MOTIVO_MAX} caracteres.`;
}
