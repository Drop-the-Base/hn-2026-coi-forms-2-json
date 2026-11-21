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

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await authFetch(path, init);
  } catch {
    throw new ApiError(0, "Brak połączenia z serwerem. Spróbuj ponownie.");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : `Serwer zwrócił błąd ${response.status}.`,
    );
  }
  return body as T;
}

export const getConfig = () => apiFetch<ApiConfig>("/config");

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
