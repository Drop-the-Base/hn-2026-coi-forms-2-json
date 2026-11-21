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

/** `exp` from the JWT payload, null without one (JWT_TTL_SECONDS=0). The API checks the signature. */
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
