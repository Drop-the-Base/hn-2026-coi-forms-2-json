import { useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router";
import { setToken, tokenProblem } from "../../shared/api/token";
import "./LoginPage.css";

/** Pasting the token printed by `issue_token` (FR-10); there are no user accounts. */
export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(
    (location.state as { error?: string } | null)?.error ?? null,
  );
  const [visible, setVisible] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = String(new FormData(event.currentTarget).get("token")).trim();
    const problem = tokenProblem(token);
    if (problem) {
      setError(problem);
      input.current?.focus();
      return;
    }
    setToken(token);
    void navigate("/", { replace: true });
  }

  return (
    <div className="login">
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
                Wklej token dostępu, który dostałeś od administratora.
              </p>
            </div>

            {error && (
              <div className="alert alert--error" role="alert" id="token-msg">
                <span className="i i-x-circle" aria-hidden="true"></span>
                <p>{error}</p>
              </div>
            )}

            <form onSubmit={onSubmit} noValidate>
              <div className="field">
                <label className="field__label" htmlFor="token">
                  Token dostępu
                </label>
                <div className="input-row">
                  <input
                    ref={input}
                    className="input input--mono"
                    id="token"
                    name="token"
                    type={visible ? "text" : "password"}
                    autoComplete="off"
                    spellCheck={false}
                    autoFocus
                    aria-invalid={error ? true : undefined}
                    aria-describedby={error ? "token-msg" : "token-hint"}
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
                <p className="field__hint" id="token-hint">
                  Token zaczyna się od „eyJ”. Nie zapisujemy go po zamknięciu
                  karty.
                </p>
              </div>
              <button className="btn btn--primary" type="submit">
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
