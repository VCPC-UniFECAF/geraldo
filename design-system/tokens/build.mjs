// Gera dist/tokens.css, dist/tailwind.preset.cjs e dist/GeraldoTokens.cs a partir de tokens.json.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const quote = (f) => (/\s/.test(f) ? `'${f}'` : f);
const stack = (fonts) => fonts.map(quote).join(", ");

function flatColors(color) {
  const out = [];
  for (const [k, v] of Object.entries(color)) {
    if (typeof v === "string") out.push([k, v]);
    else for (const [step, hex] of Object.entries(v)) out.push([`${k}-${step}`, hex]);
  }
  return out;
}

const pascal = (name) => name.split("-").map((p) => p[0].toUpperCase() + p.slice(1)).join("");

function cssFile(t) {
  const lines = [":root {"];
  for (const [name, hex] of flatColors(t.color)) lines.push(`  --${name}: ${hex};`);
  lines.push(`  --font-display: ${stack(t.font.display)};`, `  --font-body: ${stack(t.font.body)};`);
  for (const [k, v] of Object.entries(t.radius)) lines.push(`  --radius-${k}: ${v};`);
  for (const [k, v] of Object.entries(t.shadow)) lines.push(`  --shadow-${k}: ${v};`);
  for (const [k, v] of Object.entries(t.size)) lines.push(`  --${k}: ${v};`);
  lines.push("}", "");
  return `/* Gerado por design-system/tokens/build.mjs. Não edite à mão. */\n${lines.join("\n")}`;
}

function presetFile(t) {
  const preset = {
    theme: {
      extend: {
        colors: t.color,
        fontFamily: { display: t.font.display, sans: t.font.body },
        borderRadius: t.radius,
        boxShadow: t.shadow,
        minHeight: { controle: t.size["altura-controle"] },
        minWidth: { controle: t.size["altura-controle"] },
        screens: t.screens,
      },
    },
  };
  return `// Gerado por design-system/tokens/build.mjs. Não edite à mão.\nmodule.exports = ${JSON.stringify(preset, null, 2)};\n`;
}

function csFile(t) {
  const hexByte = (h, i) => `0x${h.slice(1 + i * 2, 3 + i * 2).toUpperCase()}`;
  const fields = flatColors(t.color).map(
    ([name, hex]) => `        public static readonly Color32 ${pascal(name)} = new Color32(${hexByte(hex, 0)}, ${hexByte(hex, 1)}, ${hexByte(hex, 2)}, 0xFF);`,
  );
  return `// Gerado por design-system/tokens/build.mjs. Não edite à mão.\nusing UnityEngine;\n\nnamespace Geraldo\n{\n    public static class GeraldoTokens\n    {\n${fields.join("\n")}\n    }\n}\n`;
}

export function build(tokens, outDir) {
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "tokens.css"), cssFile(tokens));
  writeFileSync(join(outDir, "tailwind.preset.cjs"), presetFile(tokens));
  writeFileSync(join(outDir, "GeraldoTokens.cs"), csFile(tokens));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const here = dirname(fileURLToPath(import.meta.url));
  const tokens = JSON.parse(readFileSync(join(here, "tokens.json"), "utf8"));
  build(tokens, join(here, "..", "dist"));
  console.log("tokens gerados em design-system/dist/");
}
