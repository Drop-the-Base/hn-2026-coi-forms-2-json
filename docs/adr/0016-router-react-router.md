# ADR-0016: Routing we frontendzie: React Router

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: FR-E4

## Kontekst

[ADR-0011](0011-frontend-react-vite.md) i [architecture.md §6](../architecture.md#6-frontend) zakładają router w `src/app/`, ale nie wskazują biblioteki. Potrzebujemy kilku prostych widoków (upload, lista zadań, wynik), bez SSR.

## Decyzja

`react-router` (licencja MIT) w trybie biblioteki: `createBrowserRouter` + `RouterProvider`. Trasy w `src/app/routes.tsx`. Bez trybu frameworkowego (to SSR i własny build, patrz odrzucony Next.js w ADR-0011).

Licencje zależności dev przy okazji szkieletu: `vite` ciągnie `lightningcss` (MPL-2.0) jako niezmodyfikowane narzędzie budowania, które nie trafia do wynikowych plików. To przypadek „dozwolone warunkowo” z [ADR-0013](0013-polityka-licencji.md). Pozostałe zależności dev mają licencje permisywne (MIT, ISC, BSD, Apache-2.0, BlueOak-1.0.0, 0BSD, CC-BY-4.0 dla danych `caniuse-lite`).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| TanStack Router | typowane trasy, ale generator tras i więcej konfiguracji niż potrzeba przy kilku widokach |
| Brak routera (stan w `useState`) | brak linków do konkretnego zadania i działania przycisku „wstecz” |

## Konsekwencje

- Standardowe API znane obu osobom w zespole, mało kodu.
- Parametry tras nie są typowane tak mocno jak w TanStack Router. Przy kilku trasach to akceptowalne.
