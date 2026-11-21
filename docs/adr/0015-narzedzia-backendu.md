# ADR-0015: Narzędzia backendu: uv, ruff, mypy, pytest, pydantic-settings

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-01, NFR-05, NFR-08, NFR-12

## Kontekst

[coding-rules.md §2.1](../coding-rules.md#21-narzędzia) wymienia narzędzia backendu, ale żadne nie miało ADR-a. Potrzebujemy zarządzania zależnościami z lockfile'em (NFR-05), lintera i formatera, sprawdzania typów, testów i jednego miejsca konfiguracji (NFR-08).

## Decyzja

| Cel | Narzędzie | Licencja |
|---|---|---|
| Zależności, środowisko, Python 3.14, build (`uv_build`) | uv | MIT OR Apache-2.0 |
| Lint + format | ruff | MIT |
| Typy | mypy (`strict = true`, plugin pydantic) | MIT |
| Testy, znaczniki `integration` i `evals` | pytest | MIT |
| Konfiguracja ze zmiennych środowiskowych | pydantic-settings | MIT |

Wersje przypięte w `backend/uv.lock`. Konfiguracja narzędzi w `backend/pyproject.toml`. Domyślny `pytest` pomija testy `integration` i `evals`; uruchamia się je przez `pytest -m integration` / `pytest -m evals`.

Zależności przechodnie mają licencje MIT, BSD, Apache-2.0 i PSF. Wyjątek: `pathspec` (MPL-2.0), zależność mypy, tylko w grupie dev, niezmodyfikowana. Dopisana do wyjątków w [ADR-0013](0013-polityka-licencji.md).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Poetry, pip-tools | wolniejsze, osobno trzeba instalować Pythona 3.14 |
| black + isort + flake8 | trzy narzędzia zamiast jednego ruffa |
| pyright | wymaga Node, mypy ma plugin pydantic |
| `os.environ` ręcznie | brak walidacji typów i zakresów na granicy konfiguracji |

## Konsekwencje

- Jedno polecenie `uv sync` stawia środowisko z dokładnymi wersjami.
- Aktualizacja zależności to świadomy `uv lock --upgrade` w osobnym PR-ze.
