import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { build } from "../tokens/build.mjs";

const tokens = JSON.parse(readFileSync(new URL("../tokens/tokens.json", import.meta.url)));
const out = mkdtempSync(join(tmpdir(), "gd-"));
build(tokens, out);
const css = readFileSync(join(out, "tokens.css"), "utf8");
const preset = readFileSync(join(out, "tailwind.preset.cjs"), "utf8");
const cs = readFileSync(join(out, "GeraldoTokens.cs"), "utf8");

test("tokens.css tem variáveis de cor, fonte, raio e sombra", () => {
  assert.match(css, /--azul-500: #3A66E8;/);
  assert.match(css, /--vermelho-500: #D92D3A;/);
  assert.match(css, /--fundo: #F4F6FB;/);
  assert.match(css, /--font-display: 'Plus Jakarta Sans', system-ui, sans-serif;/);
  assert.match(css, /--radius-card: 16px;/);
  assert.match(css, /--shadow-card: 0 1px 2px/);
});

test("preset do Tailwind carrega e expõe as chaves esperadas", async () => {
  const mod = await import(pathToFileURL(join(out, "tailwind.preset.cjs")).href);
  const theme = (mod.default ?? mod).theme.extend;
  assert.equal(theme.colors.azul[500], "#3A66E8");
  assert.equal(theme.colors.fundo, "#F4F6FB");
  assert.equal(theme.borderRadius.card, "16px");
  assert.equal(theme.minHeight.controle, "44px");
  assert.equal(theme.minWidth.controle, "44px");
  assert.deepEqual(theme.fontFamily.display, ["Plus Jakarta Sans", "system-ui", "sans-serif"]);
  assert.equal(theme.screens.md, "768px");
  assert.ok(preset.includes("module.exports"));
});

test("GeraldoTokens.cs tem Color32 para cada cor", () => {
  assert.match(cs, /public static readonly Color32 Azul500 = new Color32\(0x3A, 0x66, 0xE8, 0xFF\);/);
  assert.match(cs, /public static readonly Color32 Fundo = new Color32\(0xF4, 0xF6, 0xFB, 0xFF\);/);
  assert.match(cs, /namespace Geraldo/);
});
