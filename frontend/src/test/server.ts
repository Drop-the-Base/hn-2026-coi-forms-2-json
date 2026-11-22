import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** A slice of the official schema (backend schema.json), with its K-09 typo, enough for the tests. */
export const FORM_SCHEMA = {
  type: "object",
  properties: {
    title: { type: "string" },
    tabs: {
      type: "array",
      items: {
        type: "object",
        properties: {
          questions: {
            type: "array",
            items: {
              type: "object",
              properties: {
                field: {
                  type: "object",
                  properties: {
                    repetingSectionGrid: { type: "array", items: {} },
                  },
                },
              },
            },
          },
        },
      },
    },
  },
};

// Default API for tests; a test overrides single endpoints with server.use().
export const server = setupServer(
  http.get("*/api/v1/config", () =>
    HttpResponse.json({ max_upload_bytes: MAX_UPLOAD_BYTES }),
  ),
  http.get("*/api/v1/form-schema", () => HttpResponse.json(FORM_SCHEMA)),
  http.post("*/api/v1/login", async ({ request }) => {
    const { password } = (await request.json()) as { password: string };
    return password === TEST_PASSWORD
      ? HttpResponse.json({ token: fakeToken() })
      : HttpResponse.json({ detail: "Nieprawidłowe hasło." }, { status: 401 });
  }),
);

export const TEST_PASSWORD = "haslo-urzednika";

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
