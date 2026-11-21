# ADR-0026: Frontend: typy API z `openapi-typescript`, MSW w testach, CSS z design systemu zamiast Tailwind

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-E4, FR-10, FR-T3, NFR-02, NFR-15

## Kontekst

Pierwszy przepływ frontendu (#49, #50, #51: logowanie tokenem, upload, lista zadań) potrzebuje typów API, mocków API w testach i stylów. [ADR-0011](0011-frontend-react-vite.md) wymienia `openapi-typescript`, MSW oraz shadcn/ui + Tailwind, ale bez wersji, licencji i sposobu użycia. Design system ([frontend/DESIGN.md](../../frontend/DESIGN.md)) jest już gotowy jako zwykły CSS na zmiennych: `design/tokens.css` i `design/ui.css`.

## Decyzja

| Zależność | Rola | Licencja |
|---|---|---|
| `openapi-typescript` 7 (dev) | generuje `src/shared/api/schema.d.ts` z OpenAPI FastAPI | MIT |
| `msw` 3 (dev) | mockuje `/api/v1/*` w testach Vitest (`src/test/server.ts`) | MIT |

- **Typy API**: `frontend/openapi.json` jest zacommitowany, więc CI i build nie potrzebują backendu. Po zmianie API w `frontend/`: `npm run api:openapi` (eksport z `create_app().openapi()` przez `uv run --project ../backend`), potem `npm run api:types`. Oba pliki są wyłączone z Prettiera.
- `openapi-typescript` 7.13 deklaruje peer `typescript@^5`, a projekt ma TypeScript 6. Wpis `overrides` w `package.json` podstawia nasz TypeScript; generator działa poprawnie (sprawdzone na naszym schemacie).
- **Klient HTTP**: cienki `fetch` w `src/shared/api/client.ts` z nagłówkiem `Authorization: Bearer`, błąd jako `ApiError` z polskim `detail` z API. Bez `openapi-fetch`: trzy endpointy nie uzasadniają kolejnej zależności.
- **MSW zamiast ręcznego mockowania `fetch`**: testy przechodzą przez prawdziwy klient (nagłówki, URL, kody błędów, multipart), a ADR-0011 i coding-rules §3.1 już wskazują MSW.
- **Style**: tokeny importujemy wprost z `design/tokens.css` (bez kopii), komponenty bazowe są przeniesione z `design/ui.css` do `src/styles/ui.css`, style ekranów leżą obok komponentów w `features/*`. Tailwind i shadcn/ui z ADR-0011 odkładamy: design system jest już w CSS, więc framework niczego by nie dodał, a byłby nową zależnością i krokiem buildu.
- **Font**: stos systemowy z `--font-body`. Atkinson Hyperlegible (OFL 1.1) wymaga osobnej decyzji (licencja spoza listy z [ADR-0013](0013-polityka-licencji.md) i self-hosting).

Licencje zależności przechodnich nowych paczek: MIT, ISC, Apache-2.0, BSD, BlueOak-1.0.0, Python-2.0 (`argparse`, odpowiednik PSF), `(MIT OR CC0-1.0)`. Nic zakazanego.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `openapi-fetch` / `openapi-react-query` | typowany klient, ale przy 3 endpointach ręczny `fetch` z typami jest krótszy |
| Ręczne mockowanie `fetch` w testach | mniej zależności, ale testy omijają prawdziwy klient i nie łapią błędów URL/nagłówków |
| Generowanie typów z działającego backendu w CI | CI frontendu musiałoby stawiać backend |
| Tailwind + shadcn/ui teraz | przepisywanie gotowego CSS na klasy narzędziowe bez zysku dla urzędnika |

## Konsekwencje

- Zmiana kontraktu API wymaga regeneracji dwóch plików; bez tego typy będą nieaktualne (CI tego nie wykrywa).
- `overrides` trzeba usunąć, gdy `openapi-typescript` zacznie wspierać TypeScript 6.
- ADR-0011 w części „Komponenty: shadcn/ui” jest zawieszony do czasu akceptacji tego ADR; po akceptacji ADR-0011 dostaje dopisek o zastąpieniu tej części.
