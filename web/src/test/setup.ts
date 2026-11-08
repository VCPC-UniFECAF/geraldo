import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { reiniciarMocks } from "../api/mocks/handlers";
import { server } from "../api/mocks/server";

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  reiniciarMocks();
});
afterAll(() => server.close());
