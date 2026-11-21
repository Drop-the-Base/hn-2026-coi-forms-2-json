# Zasady pisania kodu

Obowiązują ludzi i agentów. Jakość kodu to 20% oceny (Z 8). Nowa biblioteka albo framework wymaga ADR ([adr/README.md](adr/README.md)).

## 1. Zasady ogólne

1. **Czytelność przed sprytem.** Kod czyta jury, Kuba, Benek i agenci. Pipeline musi dać się zrozumieć czytając go od góry do dołu, bez debuggera.
2. **KISS.** Najprostsze rozwiązanie, które w pełni działa. Jedna funkcja robi jedną rzecz.
3. **YAGNI.** Nie dodajemy opcji, warstw ani konfiguracji „na przyszłość". Nowa abstrakcja powstaje dopiero przy drugim realnym użyciu, chyba że jest portem z [architecture.md §5](architecture.md#5-architektura-heksagonalna-backend).
4. **SOLID**, w praktyce:
   - **S**: jeden moduł = jeden powód do zmiany (adapter PDF nie zna LLM-a).
   - **O**: nowy format pliku albo nowy model to nowy adapter, bez zmian w domenie.
   - **L**: każdy adapter da się podstawić pod swój port, a testy portu przechodzą dla każdej implementacji.
   - **I**: małe porty. `DocumentReader` czyta dokument, nie robi OCR-a ani nie woła LLM-a.
   - **D**: `application` zależy od portów (ABC), konkretne klasy wstrzykuje `bootstrap.py`.
5. **Język:** identyfikatory, komentarze i docstringi po angielsku. Dokumentacja w `docs/` po polsku. Wyjątek: terminy z formatu wyjściowego (`techName`, `repeatingSectionGrid`) zostają dokładnie jak w specyfikacji.
6. **Komentarze jak u seniora.** Komentarz wyjaśnia **dlaczego**, nie **co**. Piszemy go, gdy:
   - kod obchodzi niespójność danych lub specyfikacji (podaj źródło, np. `# Reference JSONs use repeatingSectionGrid; the schema's "repetingSectionGrid" is a typo.`);
   - decyzja nie wynika z kodu (próg, kolejność, wyjątek z reguły);
   - krok pipeline'u ma kontrakt wejścia i wyjścia: wtedy krótki docstring klasy.

   Nie komentujemy oczywistości ani zakomentowanego kodu. Skrót z ograniczeniem opisujemy tak: `# shortcut: <ograniczenie>, <kiedy to zmienić>`.

## 2. Backend (Python 3.14)

### 2.1 Narzędzia

| Cel | Narzędzie | Reguła |
|---|---|---|
| Zależności i środowisko | `uv` | lockfile w repo, wersje przypięte |
| Lint + format | `ruff` (`ruff check`, `ruff format`) | zero ostrzeżeń na `main` |
| Typy | `mypy --strict` | pełne adnotacje w `src/`, bez `Any` w domenie |
| Testy | `pytest` | patrz §2.6 |
| Modele danych i walidacja | `pydantic` v2 | na granicach systemu (HTTP, wiadomości, wyjście LLM, konfiguracja); w domenie tylko modele-kontrakty z LLM ([ADR-0020](adr/0020-pydantic-w-domenie.md)) |
| Konfiguracja | `pydantic-settings` | jedna klasa `Settings`, wartości ze zmiennych środowiskowych |

### 2.2 Architektura heksagonalna

- Warstwy: `domain` ← `application` ← `adapters`. Import w drugą stronę to błąd przeglądu.
- `domain/` nie importuje FastAPI, aio-pika, httpx, pydantic-settings ani niczego z `adapters/`. Jedyny wyjątek to `pydantic` w modelach, które są kontraktem z LLM-em (dziś `FormDraft`), patrz [ADR-0020](adr/0020-pydantic-w-domenie.md).
- Port to klasa `ABC` w `application/ports/` z metodami `@abstractmethod`. Adapter dziedziczy po porcie.
- Konkretne adaptery tworzy tylko `bootstrap.py`. Przy starcie instancjonuje wszystkie, więc brakująca metoda daje `TypeError` od razu, a nie przy pierwszym żądaniu.
- Wymiana dostawcy (inny model, OCR, broker) to nowy adapter + zmiana w `bootstrap.py` i konfiguracji. Nic więcej.

```python
# application/ports/document_reader.py
from abc import ABC, abstractmethod

from forms2json.domain.document import NormalizedDocument


class DocumentReader(ABC):
    """Turns raw file bytes into a format-independent document."""

    @abstractmethod
    def supports(self, mime_type: str) -> bool: ...

    @abstractmethod
    def read(self, content: bytes) -> NormalizedDocument: ...
```

```python
# adapters/outbound/readers/docx_reader.py
class DocxReader(DocumentReader):
    def supports(self, mime_type: str) -> bool:
        return mime_type == DOCX_MIME

    def read(self, content: bytes) -> NormalizedDocument:
        ...
```

### 2.3 Pipeline

- Każdy krok to klasa dziedzicząca po `PipelineStep` (ABC) z jedną metodą publiczną `run`.
- Krok przyjmuje i zwraca typy z domeny (`NormalizedDocument`, `FormDraft`, `FormDefinition`). Nie przekazujemy słowników `dict[str, Any]` między krokami.
- Krok nie wie, który krok jest przed nim ani po nim. Kolejność ustala tylko definicja pipeline'u.
- Każdy krok działa w osobnym spanie OTel z nazwą kroku.
- Logika deterministyczna (layout, UUID, JSONata, bloki Standardów) jest w domenie i ma testy jednostkowe. LLM nie generuje tego, co da się policzyć kodem.

### 2.4 LLM

- Wywołania LLM tylko przez port `LlmClient`. Adapter mówi z runtime'em bezpośrednio przez API zgodne z OpenAI i zapisuje tokeny w atrybutach OTel `gen_ai.usage.*`.
- Guardrails są nasze, w kodzie: limit długości wejścia, walidacja wyjścia pydantikiem, wyłącznik `LLM_ENABLED=false` (pipeline zwraca wtedy szkielet z bloków Standardów i niski confidence).
- Wyjście LLM zawsze strukturalne: JSON Schema z modelu pydantic w domenie (`model_json_schema()`, tryb strict: bez wartości domyślnych, `extra="forbid"`). Waliduj je tym samym modelem i nie ufaj mu bez walidacji ([ADR-0020](adr/0020-pydantic-w-domenie.md)).
- Prompty trzymamy w osobnych plikach (`prompts/*.md`) z wersją w nazwie albo nagłówku. Zmiana promptu = uruchomienie evali.
- Żadnych kluczy API zewnętrznych dostawców w kodzie ani w konfiguracji domyślnej (NFR-03).

### 2.5 Błędy, logi, bezpieczeństwo

- Walidujemy dane na granicach: HTTP (nazwa, rozmiar, MIME), wiadomość z kolejki, wyjście LLM. W środku ufamy typom.
- Własne wyjątki domenowe (`UnsupportedFileType`, `ExtractionFailed`…). Adapter HTTP mapuje je na kody HTTP w jednym miejscu.
- Nie łapiemy `Exception` bez ponownego rzucenia albo zalogowania z kontekstem.
- Logi przez `logging` z mostkiem OTel. Nie logujemy treści plików ani danych osobowych.
- Sekrety tylko ze zmiennych środowiskowych (NFR-07). Plik usuwany w `finally` (NFR-06).

### 2.6 Testy

| Rodzaj | Co | Zasada |
|---|---|---|
| Jednostkowe | domena, kroki pipeline'u | fałszywe adaptery (`Fake*` dziedziczące po porcie), bez sieci |
| Kontraktowe portów | każdy adapter danego portu | ten sam zestaw testów dla każdej implementacji (L z SOLID) |
| Integracyjne | adaptery z prawdziwą usługą (RabbitMQ, LLM) | znacznik `@pytest.mark.integration`, uruchamiane w compose |
| Ewaluacje | jakość wyniku na zbiorze danych | [ADR-0010](adr/0010-ewaluacje-pytest.md), nie blokują merge'a, ale wynik idzie do opisu PR-a zmieniającego pipeline lub prompty |

Nowa logika z rozgałęzieniem, pętlą albo parsowaniem ma test. Test sprawdza zachowanie, nie implementację.

## 3. Frontend

Stos i uzasadnienie: [ADR-0011](adr/0011-frontend-react-vite.md).

### 3.1 Narzędzia

| Cel | Narzędzie |
|---|---|
| Build i dev server | Vite |
| Język | TypeScript, `strict: true` |
| Lint | ESLint (flat config) + `typescript-eslint` + `eslint-plugin-react-hooks` |
| Format | Prettier |
| Testy jednostkowe i komponentów | Vitest + React Testing Library |
| Mockowanie API w testach | MSW |
| E2E | Playwright |
| Typy API | `openapi-typescript` z OpenAPI FastAPI |

### 3.2 Struktura

- **Folder per funkcja (feature)**, nie per typ pliku: `features/upload`, `features/jobs`, `features/review`, `features/form-preview`.
- Feature trzyma razem komponenty, hooki, zapytania API i testy. Import z innego feature'a tylko przez jego `index.ts`.
- `shared/` zawiera tylko to, czego używają co najmniej dwa feature'y.
- Zaczynamy płasko. Podział na podfoldery dopiero, gdy feature ma więcej niż ok. 7 plików.

### 3.3 Stan i dane

- **Stan serwera** (zadania, wyniki) tylko przez TanStack Query. Komponenty nie wołają `fetch` bezpośrednio, tylko hooki z `features/*/api/`.
- **Stan lokalny UI**: `useState` / `useReducer`. Globalny store (np. Zustand) dopiero, gdy stan muszą dzielić niezależne części drzewa. Wtedy ADR.
- Typy odpowiedzi API pochodzą z wygenerowanego pliku. Nie piszemy ich ręcznie.
- Wynikowy JSON walidujemy w przeglądarce tym samym JSON Schema co backend.

### 3.4 Komponenty

- Komponenty funkcyjne, jeden komponent eksportowany na plik, nazwa pliku = nazwa komponentu.
- Komponent prezentacyjny dostaje dane przez propsy i nie pobiera danych sam. Pobieraniem zajmuje się komponent-kontener albo hook.
- Bez `useEffect` do wyliczania danych z propsów: liczymy je w trakcie renderu.
- Dostępność (NFR-15): semantyczny HTML, etykiety pól, obsługa klawiatury, kontrast. Test e2e sprawdza główny scenariusz klawiaturą.

## 4. Git i przegląd

- Workflow branchy, issues i PR-ów: [AGENTS.md](../AGENTS.md).
- Małe PR-y: jeden PR = jedno issue.
- Przed PR: `ruff check`, `ruff format --check`, `mypy`, `pytest` (backend); `eslint`, `prettier --check`, `vitest` (frontend). Wszystko zielone.
- Przegląd zmian: skill `ponytail-review`.
