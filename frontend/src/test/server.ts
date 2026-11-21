import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

// Default API for tests; a test overrides single endpoints with server.use().
export const server = setupServer(
  http.get("*/api/v1/config", () =>
    HttpResponse.json({ max_upload_bytes: MAX_UPLOAD_BYTES }),
  ),
);

/** Unsigned JWT-shaped token; only the API checks the signature. */
export function fakeToken(expiresInSeconds = 3600) {
  const payload = btoa(
    JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expiresInSeconds }),
  );
  return `eyJhbGciOiJIUzI1NiJ9.${payload}.signature`;
}
