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

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    // Absolute URL because fetch in Node (tests) rejects relative ones; in the browser it is the same origin.
    response = await fetch(new URL(`/api/v1${path}`, location.origin), {
      ...init,
      headers,
    });
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

export function submitJob(file: File) {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<JobAccepted>("/jobs", { method: "POST", body });
}
