import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

async function start() {
  // `npm run dev:demo` liga a API simulada no navegador (usuário medico1, senha demo).
  if (import.meta.env.MODE === "demo") {
    const { worker } = await import("./api/mocks/browser");
    await worker.start({ onUnhandledFrame: "bypass" });
  }
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

start();
