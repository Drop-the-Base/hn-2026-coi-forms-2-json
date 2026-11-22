# ADR-0033: Dostępność frontendu: `eslint-plugin-jsx-a11y` w lincie, `axe-core` w testach Vitest

- Status: Proponowana
- Data: 2026-11-22
- Wymagania: FR-E4, FR-T2, NFR-15

## Kontekst

Panel urzędnika ma spełniać WCAG 2.1 AA (ustawa o dostępności cyfrowej podmiotów publicznych, #176). Kontrast tokenów sprawdza już `frontend/design/kontrast.py`, ale reszty (etykiety, role, kolejność nagłówków, tytuł strony, obsługa klawiaturą) nic automatycznie nie pilnowało.

## Decyzja

| Zależność | Rola | Licencja |
|---|---|---|
| `eslint-plugin-jsx-a11y` 6 (dev) | reguły `recommended` w `eslint.config.js`, statyczna kontrola JSX | MIT |
| `axe-core` 4 (dev) | `src/test/axe.ts`: reguły WCAG 2.0/2.1 A i AA na wyrenderowanym DOM w Vitest (`src/app/a11y.test.tsx`) | MPL-2.0, wyjątek warunkowy w [ADR-0013](0013-polityka-licencji.md) |

- `axe-core` wołamy bezpośrednio (`axe.run(document)`), bez nakładki typu `vitest-axe`: cały helper ma kilka linii.
- Reguła `color-contrast` jest wyłączona w testach, bo jsdom nie liczy układu. Kontrast pilnuje `kontrast.py` na tokenach.
- `eslint-plugin-jsx-a11y` 6.10 deklaruje peer `eslint@^9`, a projekt ma ESLint 10. Wpis `overrides` w `package.json` podstawia nasz ESLint; reguły działają (lint przechodzi i zgłasza błędy).
- Wyłączenia reguł tylko w linii, z komentarzem dlaczego (np. roving tabindex w `tablist`, skrót myszą w podglądzie z odpowiednikiem w liście struktury).

Licencje zależności przechodnich: MIT, ISC, Apache-2.0, BSD-2-Clause oraz `language-subtag-registry` na CC0-1.0 (domena publiczna, same dane). Nic zakazanego.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `vitest-axe` (MIT) | nakładka na kilka linii, ostatnie wydanie 0.1.0, i tak ciągnie `axe-core` |
| `eslint-plugin-jsx-a11y-x` (fork z peerem ESLint 10) | młody fork; oryginał działa z `overrides` |
| `@axe-core/playwright` w e2e | przeglądarka i kontrast w prawdziwym układzie, ale e2e jeszcze nie ma w CI; do rozważenia razem z nim |
| Tylko ręczny audyt | nie łapie regresji między PR-ami |

## Konsekwencje

- Każdy nowy ekran dostaje test w `src/app/a11y.test.tsx`; lint blokuje typowe błędy w JSX.
- Testy w jsdom nie zastąpią sprawdzenia klawiaturą i czytnikiem ekranu (lista w README, „Deklaracja dostępności”).
- `overrides` usuwamy, gdy `eslint-plugin-jsx-a11y` zacznie wspierać ESLint 10.
