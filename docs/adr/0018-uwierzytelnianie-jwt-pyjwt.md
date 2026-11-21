# ADR-0018: Uwierzytelnianie JWT: PyJWT, HMAC, token demo ze skryptu

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-10, NFR-07, NFR-08

## Kontekst

API ma być chronione JWT, a parametry JWT konfigurowalne (FR-10, NFR-08). Nie mamy kont użytkowników ani dostawcy tożsamości. Na demo trzeba jakoś zdobyć token.

## Decyzja

- Biblioteka: **PyJWT** (licencja MIT). Do testów HTTP: **httpx2** (BSD-3-Clause, tylko grupa dev), którego wymaga `starlette.testclient` (stary `httpx` jest tam przestarzały).
- Algorytm: tylko HMAC (`HS256`/`HS384`/`HS512`), wspólny sekret. Lista algorytmów w `jwt.decode` pochodzi z konfiguracji, więc `none` i podmiana algorytmu są odrzucane.
- Konfiguracja w `config.py`: `JWT_SECRET` (wymagany, min. 32 znaki, bez wartości domyślnej), `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_TTL_SECONDS`.
- Wymagane claimy: `exp`, `iat`, `iss`, `aud`, `sub`. Każdy błąd daje 401 z `WWW-Authenticate: Bearer`.
- Ochrona endpointów: zależność FastAPI `require_jwt` z `adapters/inbound/http/auth.py`, podpinana na routerze (`APIRouter(dependencies=[Depends(require_jwt)])`).
- Token na demo: skrypt `uv run python -m forms2json.adapters.inbound.http.issue_token [subject]`. Podpisuje token tym samym sekretem z env.

Zależności przechodnie nowych pakietów: starlette (BSD-3), anyio (MIT), idna (BSD-3), annotated-doc (MIT), opentelemetry-api (Apache-2.0); w dev: httpcore2 (BSD-3), h11 (MIT), truststore (MIT). Wszystkie zgodne z [ADR-0013](0013-polityka-licencji.md).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| python-jose | słabo utrzymywana, historia podatności |
| Authlib | duża biblioteka OAuth, potrzebujemy tylko weryfikacji JWT |
| joserfc | mniej popularna, PyJWT wystarcza |
| RS256 z parą kluczy | brak zewnętrznego wystawcy tokenów, HMAC prostszy w konfiguracji |
| Endpoint `POST /token` z loginem | wymaga kont i haseł, których nie mamy; otwarty endpoint wydający tokeny niweczyłby ochronę |

## Konsekwencje

- Aplikacja bez `JWT_SECRET` nie wystartuje. Testy dostają sekret z `tests/conftest.py`.
- Kto zna sekret, może wydać token. Dla produkcji z prawdziwymi użytkownikami trzeba zewnętrznego IdP i algorytmu asymetrycznego (nowy ADR).
- Nie ma odwoływania tokenów przed `exp`. Krótki `JWT_TTL_SECONDS` ogranicza ryzyko.
