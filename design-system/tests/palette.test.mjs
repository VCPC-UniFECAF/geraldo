import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { contrastRatio } from "../tokens/contrast.mjs";

const tokens = JSON.parse(readFileSync(new URL("../tokens/tokens.json", import.meta.url)));
const flat = (obj, path = []) =>
  Object.entries(obj).flatMap(([k, v]) => (typeof v === "string" ? [[[...path, k].join("-"), v]] : flat(v, [...path, k])));
const colors = Object.fromEntries(flat(tokens.color));
const lightness = (name) => contrastRatio(colors[name], "#000000"); // quanto maior, mais claro

test("nenhuma cor da paleta é branco ou preto puro", () => {
  for (const [name, hex] of Object.entries(colors)) {
    assert.ok(!["#FFFFFF", "#000000"].includes(hex.toUpperCase()), `${name} = ${hex}`);
  }
});

test("os tons de branco ficam do mais claro para o mais escuro", () => {
  const order = ["branco", "fundo", "neutro-50", "neutro-100"];
  for (let i = 1; i < order.length; i++) {
    assert.ok(lightness(order[i - 1]) > lightness(order[i]), `${order[i - 1]} deveria ser mais claro que ${order[i]}`);
  }
});

test("o branco dos cards é suave: se distingue do branco puro", () => {
  assert.ok(contrastRatio(colors.branco, "#FFFFFF") > 1.0, "branco não pode ser #FFFFFF");
  assert.ok(contrastRatio(colors.branco, "#FFFFFF") < 1.1, "branco suave não pode ficar escuro demais");
});
