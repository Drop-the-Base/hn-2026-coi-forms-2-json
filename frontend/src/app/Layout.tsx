import { useQueryClient } from "@tanstack/react-query";
import { Navigate, NavLink, Outlet, useNavigate } from "react-router";
import { formatTime, getToken, tokenExpiry } from "../shared/api/token";

export function Layout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const token = getToken();
  if (!token) return <Navigate to="/logowanie" replace />;
  const expiry = tokenExpiry(token);

  function logout() {
    sessionStorage.clear(); // token and the session's job list
    queryClient.clear();
    void navigate("/logowanie", { replace: true });
  }

  return (
    <>
      <header className="shell">
        <div className="shell__in">
          <span className="wordmark">
            forms2json <span>blankiet do eUsługi</span>
          </span>
          <nav aria-label="Główna">
            <NavLink to="/" end>
              Zadania
            </NavLink>
          </nav>
          <div className="shell__end">
            {expiry && (
              <span className="who">Sesja do {formatTime(expiry)}</span>
            )}
            <button type="button" onClick={logout}>
              <span className="i i-log-out" aria-hidden="true"></span>Wyloguj
            </button>
          </div>
        </div>
      </header>
      <Outlet />
    </>
  );
}
