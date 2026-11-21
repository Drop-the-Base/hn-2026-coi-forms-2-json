# ADR-0011: Frontend: React + Vite + TypeScript + TanStack Query

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: FR-E4, FR-E5, FR-T1, FR-T2, NFR-15, NFR-07

## Kontekst

Frontend to narzędzie dla urzędnika: upload, status zadania, edytor JSON, podgląd formularza i podświetlanie niskiego confidence. Nie potrzebuje SEO ani renderowania po stronie serwera. Ma być prosty we wdrożeniu (statyczne pliki) i czytelny.

## Decyzja

| Obszar | Wybór | Licencja |
|---|---|---|
| Framework | React | MIT |
| Build | Vite, wynik serwowany przez `nginxinc/nginx-unprivileged` (Alpine, bez roota) | MIT / BSD |
| Język | TypeScript `strict` | Apache-2.0 |
| Stan serwera | TanStack Query | MIT |
| Stan lokalny | `useState` / `useReducer`, bez globalnego store'a (YAGNI) | — |
| Typy API | `openapi-typescript` z OpenAPI FastAPI | MIT |
| Edytor JSON | CodeMirror 6 | MIT |
| Komponenty | shadcn/ui (Radix + Tailwind), kopiowane do repo | MIT |
| Testy | Vitest, React Testing Library, MSW, Playwright | MIT / Apache-2.0 |
| Jakość | ESLint (flat config) + `typescript-eslint` + `eslint-plugin-react-hooks`, Prettier | MIT |

Struktura: folder per feature ([architecture.md §6](../architecture.md#6-frontend)), zasady w [coding-rules.md §3](../coding-rules.md#3-frontend).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Next.js | SSR i serwer Node niepotrzebne, trudniejsze wdrożenie niż statyczne pliki |
| Monaco Editor | znacznie cięższy niż CodeMirror 6 |
| Redux Toolkit / Zustand | brak współdzielonego stanu klienta, który by to uzasadniał |
| Pełny Feature-Sliced Design | za dużo warstw jak na 4 feature'y; zaczynamy od prostych folderów per feature |
| Biome zamiast ESLint + Prettier | szybszy, ale reguły `react-hooks` i ekosystem pluginów ESLint są dojrzalsze |

## Konsekwencje

- Kontrakt API ma jedno źródło prawdy (OpenAPI), a zmiana w backendzie od razu psuje typy we frontendzie.
- Podgląd formularza (FR-E5) to nasze własne komponenty renderujące `tabs/sections/fields`.
