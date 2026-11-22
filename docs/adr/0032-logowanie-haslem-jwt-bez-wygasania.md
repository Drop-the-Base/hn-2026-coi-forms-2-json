# ADR-0032: Logowanie hasłem z konfiguracji, JWT bez wygasania

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-10, NFR-07, NFR-08
- Częściowo zastępuje: [ADR-0019](0019-uwierzytelnianie-jwt-pyjwt.md) (sposób zdobycia tokenu i wymagany claim `exp`)

## Kontekst

Według [ADR-0019](0019-uwierzytelnianie-jwt-pyjwt.md) token na demo generuje się skryptem `issue_token` i wkleja na ekranie logowania, a token wygasa po `JWT_TTL_SECONDS` (domyślnie 1 h). W praktyce to przeszkadza: ktoś musi mieć dostęp do serwera, żeby wydać token, a urzędnik traci sesję w trakcie przeglądu formularza.

To projekt hackathonowy i demo: jedno wspólne konto urzędnika, bez bazy użytkowników i bez dostawcy tożsamości. FR-10 (MUST) wymaga, żeby API było chronione JWT, a parametry JWT były konfigurowalne.

## Decyzja

Urzędnik wpisuje hasło z `.env`, a API wymienia je na JWT. Token domyślnie nie wygasa.

- `APP_PASSWORD` w `config.py` (SecretStr, wymagane, min. 8 znaków, bez wartości domyślnej).
- `POST /api/v1/login` z JSON-em `{"password": "…"}`, jedyna ścieżka pod `/api/v1` bez `require_jwt`. Hasło porównujemy w stałym czasie (`hmac.compare_digest`). Złe hasło: `401 {"detail": "Nieprawidłowe hasło."}`. Dobre: `200 {"token": "<JWT>"}` z `issue_token(settings, "urzednik")`.
- `JWT_TTL_SECONDS=0` (nowa wartość domyślna) oznacza token bez `exp`. Przy wartości > 0 `exp` jest ustawiany jak dotąd.
- `require_jwt` wymaga claimów `iat`, `iss`, `aud`, `sub`. `exp` jest opcjonalny, ale jeśli jest, PyJWT go sprawdza. Podpis, algorytm z konfiguracji, `iss` i `aud` sprawdzamy bez zmian.
- Skrypt `issue_token` zostaje, dla skryptów i curla bez hasła (np. `run_eval`).
- Frontend: pole „Hasło” zamiast pola na token. Czas sesji w nagłówku pokazujemy tylko wtedy, gdy token ma `exp`.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Zostać przy wklejaniu tokenu ze skryptu (ADR-0019) | wymaga dostępu do serwera przy każdym logowaniu, a sesja wygasa w trakcie pracy |
| Konta użytkowników w bazie z hashami haseł | nie mamy bazy ani wielu użytkowników, YAGNI na demo |
| Zewnętrzny IdP (OIDC) | duża konfiguracja dla jednego wspólnego konta |
| Refresh token zamiast tokenu bez `exp` | druga ścieżka i drugi sekret do pilnowania, a wynik dla urzędnika ten sam |
| Limit prób logowania (rate limiting) | osobny mechanizm ze stanem; przy długim losowym haśle zgadywanie i tak nic nie da. Dodać przy prawdziwych użytkownikach |

## Konsekwencje

- Kto zna hasło, ma dostęp do API. Hasło musi być długie i losowe (`openssl rand -hex 12`), a każde wdrożenie musi dopisać `APP_PASSWORD` do `.env`, bo bez niego api i worker nie wystartują.
- Tokenu bez `exp` nie da się odwołać. Jedyna metoda to zmiana `JWT_SECRET` (unieważnia wszystkie tokeny). Gdy hasło wycieknie: zmienić `APP_PASSWORD` i `JWT_SECRET`, potem `docker compose up -d`.
- Token leży w `sessionStorage`, więc po zamknięciu karty urzędnik loguje się ponownie hasłem.
- Kto potrzebuje wygasania, ustawia `JWT_TTL_SECONDS` > 0. Wtedy obowiązuje dotychczasowe zachowanie z ADR-0019.
- Dla produkcji z prawdziwymi użytkownikami ta decyzja nie wystarcza (patrz ADR-0019: zewnętrzny IdP, algorytm asymetryczny, nowy ADR).
