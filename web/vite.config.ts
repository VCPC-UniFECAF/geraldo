import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // Os mocks do modo demo importam o JSON de exemplos de ../docs/contracts; o servidor de dev precisa poder ler fora de web/.
  server: { fs: { allow: [".."] } },
  test: { environment: "jsdom", globals: true, setupFiles: "./src/test/setup.ts", css: false },
});
