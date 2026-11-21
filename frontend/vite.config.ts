import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Same origin in dev, so the api needs no CORS.
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  // testTimeout: the polling test waits one real 2 s interval.
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
    testTimeout: 10_000,
  },
});
