import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { contrastRatio, PAIRS, hexOf } from "../tokens/contrast.mjs";

const tokens = JSON.parse(readFileSync(new URL("../tokens/tokens.json", import.meta.url)));

test("contrastRatio: preto sobre branco é 21", () => {
  assert.equal(Math.round(contrastRatio("#000000", "#FFFFFF")), 21);
});

test("contrastRatio é simétrico", () => {
  assert.equal(contrastRatio("#3A66E8", "#FFFFFF"), contrastRatio("#FFFFFF", "#3A66E8"));
});

for (const [fg, bg, min] of PAIRS) {
  test(`contraste ${fg} sobre ${bg} >= ${min}`, () => {
    const ratio = contrastRatio(hexOf(tokens, fg), hexOf(tokens, bg));
    assert.ok(ratio >= min, `${fg} sobre ${bg} = ${ratio.toFixed(2)} (mínimo ${min})`);
  });
}
