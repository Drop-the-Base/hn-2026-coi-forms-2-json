import type { components } from "./schema";
import { getToken } from "./token";

type Schemas = components["schemas"];
export type ApiConfig = Schemas["ApiConfig"];
export type JobAccepted = Schemas["JobAccepted"];
export type JobStatus = Schemas["JobStatus"];

/** status 0 = no response from the server. `message` is ready to show to the user. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/** fetch to the API with the session token. Rejects only when there is no response. */
function authFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  // Absolute URL because fetch in Node (tests) rejects relative ones; in the browser it is the same origin.
  return fetch(new URL(`/api/v1${path}`, location.origin), {
    ...init,
    headers,
  });
}

/** The successful response; anything else becomes an ApiError with the server's detail. */
async function okResponse(path: string, init: RequestInit) {
  let response: Response;
  try {
    response = await authFetch(path, init);
  } catch {
    throw new ApiError(0, "Brak połączenia z serwerem. Spróbuj ponownie.");
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = (body as { detail?: unknown } | null)?.detail;
    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : `Serwer zwrócił błąd ${response.status}.`,
    );
  }
  return response;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await okResponse(path, init);
  return (await response.json().catch(() => null)) as T;
}

export const getConfig = () => apiFetch<ApiConfig>("/config");

/** The official eUsługi FormDefinition JSON Schema, as published by the backend. */
export const getFormSchema = () =>
  apiFetch<Record<string, unknown>>("/form-schema");

export const getJob = (jobId: string) =>
  apiFetch<JobStatus>(`/jobs/${encodeURIComponent(jobId)}`);

/** Raw SSE response (ADR-0014): EventSource cannot send the Authorization header. */
export const getJobEvents = (jobId: string, signal: AbortSignal) =>
  authFetch(`/jobs/${encodeURIComponent(jobId)}/events`, { signal });

export function submitJob(file: File) {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<JobAccepted>("/jobs", { method: "POST", body });
}

/** The office file rendered as PDF by the API, for the review screen's "Oryginał" (ADR-0031). */
export async function getPreviewPdf(file: File) {
  const body = new FormData();
  body.append("file", file);
  const response = await okResponse("/preview", { method: "POST", body });
  return response.blob();
}
