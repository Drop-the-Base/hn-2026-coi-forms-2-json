# Zasady dla agentów - zespół H-kwadrat

## Kto pracuje na repo

Zespół H-kwadrat to dwie osoby. Każda ma swojego agenta. Agenci pracują równolegle, więc nie mogą wchodzić sobie w drogę.

| Agent | Działa w imieniu | Etykieta | Konto GitHub | Prefiks brancha |
| --- | --- | --- | --- | --- |
| agent Benka | Benek | `agent:benek` | benhus8 | `benek/` |
| agent Kuby | Kuba | `agent:kuba` | konto Kuby | `kuba/` |

**Ustal, którym agentem jesteś**, zanim cokolwiek zrobisz: `gh api user -q .login`. Wynik `benhus8` oznacza agenta Benka, każdy inny login to agent Kuby. Nie zgaduj z nazwy brancha ani z historii rozmowy.

Źródłem prawdy o zadaniach są **GitHub Issues**.

## Dokumentacja projektu: przeczytaj przed pierwszym zadaniem

| Plik | Po co |
| --- | --- |
| [docs/requirements.md](docs/requirements.md) | wymagania FR/NFR z ID, konflikty w wymaganiach i decyzje robocze |
| [docs/architecture.md](docs/architecture.md) | usługi, przepływ, pipeline, struktura katalogów |
| [docs/coding-rules.md](docs/coding-rules.md) | jak piszemy kod (backend i frontend) |
| [docs/adr/README.md](docs/adr/README.md) | rejestr decyzji: co wybraliśmy, co odrzuciliśmy i dlaczego |
| [docs/analiza-i-charakterystyka-danych.md](docs/analiza-i-charakterystyka-danych.md) | dane wejściowe, wzorcowe JSON-y, niespójności |
| [docs/propozycja-slownika.md](docs/propozycja-slownika.md) | propozycja nowego słownika `DYSCYPLINY_SPORTOWE` (FR-E2) |

Zasady:
- Issue i PR odwołują się do ID wymagań (np. `FR-08`, `NFR-06`).
- **Nowa biblioteka, framework albo usługa = nowy ADR w tym samym PR-ze.** Najpierw sprawdź [politykę licencji](docs/adr/0013-polityka-licencji.md).
- Kod niezgodny z ADR albo z coding-rules nie przechodzi przeglądu. Chcesz to zmienić? Napisz nowy ADR.

## Branie zadań
1. Wolne issue = otwarte, **bez assignee** i **bez etykiety `agent:*`**. Tylko takie wolno brać.
2. Zgarnij je: przypisz się, dodaj swoją etykietę i zostaw krótki komentarz, że bierzesz:
   `gh issue edit <N> --add-assignee @me --add-label "agent:<benek|kuba>"`
3. Sprawdź jeszcze raz: `gh issue view <N> --json assignees,labels`. Jeśli drugi agent też się przypisał, wycofaj się i zostaw komentarz.
4. Issue z etykietą drugiego agenta jest zajęte. Nie ruszaj go, nie komentuj go i nie zamykaj.
5. Nie bierz zadań na zapas: tylko tyle, ile zrobisz w najbliższej godzinie.
6. Jeśli zadanie wymaga decyzji człowieka (np. rozstrzygnięcia niejasności w wymaganiach), dodaj etykietę `pytanie` i napisz w komentarzu, do kogo jest pytanie: Benek, Kuba czy obaj.

## Praca
- Branch: `<benek|kuba>/<nr issue>-<krotka-nazwa>`, np. `kuba/12-parser-docx`.
- PR z `Closes #<nr>` w opisie. Nie pushuj bezpośrednio na `main`.
- Duże issue możesz podzielić na mniejsze issues z dopiskiem `Część #<nr>` i swoją etykietą.
- Nie edytuj plików, które zmienia otwarty PR drugiego agenta. Jeśli musisz, napisz najpierw komentarz w tym PR.
- Przed merge'em: zielone testy. Konflikt z PR-em drugiego agenta rozwiązuje ten, kto merguje później.
- Merge'uje człowiek, w imieniu którego działa agent (albo agent, jeśli jego człowiek wprost na to pozwolił).

## Zbiór walidacyjny: nie ruszaj
`data/walidacja/` i `backend/tests/evals/dataset/walidacja/` to hold-out (formularze 10+, NFR-11): udają nieznane pliki z obrony.
- Nie otwieraj tych plików i nie wklejaj ich treści do promptów, reguł, testów ani issue. Nie poprawiaj niczego pod nie.
- Wolno tylko uruchomić `run_eval --forms 10,11,12` i podać liczby w PR.
- Spadek na walidacji szukasz i naprawiasz na formularzach 1–9.
- Zmiany w samym zbiorze (nowe formularze, poprawki złotych JSON-ów) robi człowiek albo agent na jego wyraźne polecenie, w osobnym PR.

## Pisanie kodu
- Zasady: [docs/coding-rules.md](docs/coding-rules.md) (KISS, YAGNI, SOLID, architektura heksagonalna z portami na ABC, czytelny pipeline).
- Przy każdym zadaniu z kodem stosuj skill **ponytail** na poziomie `full` ([.claude/skills/ponytail/SKILL.md](.claude/skills/ponytail/SKILL.md)). Przegląd zmian: `ponytail-review`, audyt repo: `ponytail-audit`.
- Przed PR (to samo puszcza CI, [.github/workflows/ci.yml](.github/workflows/ci.yml)):
  - backend (`cd backend`): `uv sync`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests`, `uv run pytest` (testy `integration` i `evals` są domyślnie pomijane, uruchom je przez `-m integration` / `-m evals`)
  - frontend (`cd frontend`): `npm ci`, `npm run lint`, `npx prettier --check .`, `npx vitest run`, `npm run build`
