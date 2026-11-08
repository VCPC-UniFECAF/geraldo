// Contraste WCAG entre pares de tokens usados nos componentes (DS §3.6).
export function hexOf(tokens, name) {
  const [group, step] = name.split("-");
  const c = tokens.color;
  return step === undefined ? c[group] : c[group][step];
}

function channel(v) {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function luminance(hex) {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}

export function contrastRatio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// [texto, fundo, mínimo]
export const PAIRS = [
  ["branco", "azul-500", 4.5],
  ["branco", "vermelho-500", 4.5],
  ["tinta", "branco", 4.5],
  ["tinta", "fundo", 4.5],
  ["neutro-500", "branco", 4.5],
  ["neutro-500", "fundo", 4.5],
  ["azul-600", "branco", 4.5],
  ["azul-700", "azul-100", 4.5],
  ["vermelho-600", "vermelho-50", 4.5],
  ["vermelho-700", "vermelho-100", 4.5],
  ["neutro-600", "neutro-50", 4.5],
  ["sucesso-700", "sucesso-50", 4.5],
  ["aviso-700", "aviso-50", 4.5],
];
