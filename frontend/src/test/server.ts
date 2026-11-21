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

/** SSE response the test feeds event by event, like GET /jobs/{id}/events (PR #101). */
export function sseStream() {
  const encoder = new TextEncoder();
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start: (c) => void (controller = c),
  });
  return {
    response: () =>
      new HttpResponse(body, {
        headers: { "Content-Type": "text/event-stream" },
      }),
    send: (data: object) =>
      controller.enqueue(
        encoder.encode(`event: progress\ndata: ${JSON.stringify(data)}\n\n`),
      ),
    close: () => controller.close(),
  };
}
