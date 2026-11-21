// sessionStorage: the token is gone when the tab closes and never lands in the URL (ekrany.md §1).
const TOKEN_KEY = "forms2json.token";

// Dev only: VITE_DEV_TOKEN in frontend/.env.development.local skips the login screen; never in a build.
const devToken: string | null = import.meta.env.DEV
  ? ((import.meta.env.VITE_DEV_TOKEN as string | undefined) ?? null)
  : null;

export const getToken = () => sessionStorage.getItem(TOKEN_KEY) ?? devToken;
export const setToken = (token: string) =>
  sessionStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);

/** `exp` from the JWT payload. The signature is checked only by the API. */
export function tokenExpiry(token: string): Date | null {
  const parts = token.split(".");
  if (parts.length !== 3 || !token.startsWith("eyJ")) return null;
  try {
    const payload: unknown = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")),
    );
    const exp = (payload as { exp?: unknown }).exp;
    return typeof exp === "number" ? new Date(exp * 1000) : null;
  } catch {
    return null;
  }
}

export const formatTime = (date: Date) =>
  date.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" });

/** Message for the login screen, or null when the token looks usable. */
export function tokenProblem(token: string, now = new Date()): string | null {
  const expiry = tokenExpiry(token);
  if (!expiry)
    return "To nie wygląda na token. Token ma trzy części rozdzielone kropkami i zaczyna się od „eyJ”.";
  if (expiry <= now)
    return `Token wygasł ${expiry.toLocaleDateString("pl-PL")} o ${formatTime(expiry)}. Poproś administratora o nowy token i wklej go poniżej.`;
  return null;
}
