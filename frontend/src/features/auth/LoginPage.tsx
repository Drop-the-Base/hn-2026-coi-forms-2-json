import { useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router";
import { ApiError, login } from "../../shared/api/client";
import { setToken } from "../../shared/api/token";
import "./LoginPage.css";

/** One shared clerk password from the server's .env, traded for a JWT (FR-10, ADR-0032). */
export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(
    (location.state as { error?: string } | null)?.error ?? null,
  );
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("password"));
    setPending(true);
    try {
      setToken((await login(password)).token);
      void navigate("/", { replace: true });
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 401
          ? "Nieprawidłowe hasło."
          : e instanceof Error
            ? e.message
            : String(e),
      );
      setPending(false);
      input.current?.focus();
    }
  }

  return (
    <div className="login">
      <title>Logowanie – forms2json</title>
      <header className="shell">
        <div className="shell__in">
          <span className="wordmark">
            forms2json <span>blankiet do eUsługi</span>
          </span>
        </div>
      </header>
      <main className="login__main">
        <div className="sheet login__sheet">
          <div className="sheet__body stack">
            <div>
              <h1>Zaloguj się</h1>
              <p className="login__lede">
                Wpisz hasło, które dostałeś od administratora.
              </p>
            </div>

            {error && (
              <div className="alert alert--error" role="alert" id="login-msg">
                <span className="i i-x-circle" aria-hidden="true"></span>
                <p>{error}</p>
              </div>
            )}

            <form onSubmit={(e) => void onSubmit(e)} noValidate>
              <div className="field">
                <label className="field__label" htmlFor="password">
                  Hasło
                </label>
                <div className="input-row">
                  <input
                    ref={input}
                    className="input"
                    id="password"
                    name="password"
                    type={visible ? "text" : "password"}
                    autoComplete="current-password"
                    spellCheck={false}
                    // The only field on the page; the user comes here to type it.
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                    autoFocus
                    aria-invalid={error ? true : undefined}
                    aria-describedby={error ? "login-msg" : undefined}
                  />
                  <button
                    className="btn btn--secondary"
                    type="button"
                    aria-pressed={visible}
                    onClick={() => setVisible(!visible)}
                  >
                    <span className="i i-eye" aria-hidden="true"></span>Pokaż
                  </button>
                </div>
              </div>
              <button
                className="btn btn--primary"
                type="submit"
                disabled={pending}
              >
                Zaloguj
              </button>
            </form>

            <p className="login__note">
              Pliki, które wgrasz, są przetwarzane tylko tymczasowo i usuwane z
              serwera po zakończeniu zadania.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
