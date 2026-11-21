# ADR-0020: Pydantic w domenie jako jedyny wyjątek od zasady „domena bez frameworków”

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: FR-07, FR-T1, NFR-12

## Kontekst

[ADR-0003](0003-architektura-heksagonalna-abc.md) i [coding-rules §2.2](../coding-rules.md#22-architektura-heksagonalna) trzymają domenę bez zależności od frameworków. Jednocześnie `FormDraft` (wynik kroku Understand) jest granicą zaufania: LLM wypełnia go przez structured output, więc potrzebujemy JSON Schema w trybie strict (wszystkie pola wymagane, `additionalProperties: false`) i walidacji odpowiedzi.

Bez pydantic trzeba było utrzymywać ręcznie trzy rzeczy, które muszą się zgadzać: dataclassy, ręczny schemat i ręczny parser. Każda zmiana pola to trzy miejsca do poprawy i ryzyko rozjazdu schematu z walidacją.

## Decyzja

W `domain/` wolno importować **tylko `pydantic`** (v2), i tylko do modeli, które są jednocześnie kontraktem z LLM-em i walidacją jego wyjścia (dziś `FormDraft`). Jeden model daje JSON Schema (`model_json_schema()`) i walidację (`model_validate`).

- Modele bez wartości domyślnych i z `ConfigDict(extra="forbid", strict=True)`, więc schemat jest strict: każde pole w `required`, `additionalProperties: false`. Pole opcjonalne to `X | None` bez domyślnej (w schemacie `anyOf` z `null`).
- Reguły ponad typy (unikalność kluczy pól, warunki odwołują się do istniejących pól, confidence 0–1) są walidatorami pydantic w tym samym modelu.
- `ValidationError` owijamy w wyjątek domenowy `InvalidFormDraft`.
- Inne modele domeny (`FormDefinition`, `NormalizedDocument`) zostają bez pydantic. Dalej zakazane w domenie: FastAPI, aio-pika, httpx, pydantic-settings, `adapters/`.

Licencja pydantic: MIT (zgodna z [ADR-0013](0013-polityka-licencji.md)), już w zależnościach przez pydantic-settings ([ADR-0015](0015-narzedzia-backendu.md)); teraz dopisany jawnie do `pyproject.toml`.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Dataclassy + ręczny schemat + ręczny parser w domenie | trzy miejsca do utrzymania, schemat i walidacja mogą się rozjechać |
| Model pydantic w `adapters/`, mapowany na dataclassy w domenie | dwa równoległe modele i mapper bez wartości dodanej; i tak walidacja musi znać reguły domeny |
| `jsonschema` do walidacji ręcznego schematu | nowa zależność, nadal ręczny schemat i osobne dataclassy |

## Konsekwencje

- Jedno źródło prawdy dla kształtu `FormDraft`: zmiana pola zmienia schemat i walidację naraz.
- Domena zależy od pydantic. Wyjątek jest wąski: nowy model pydantic w domenie musi być kontraktem z LLM-em, inaczej to błąd przeglądu.
- Schemat używa `$defs`/`$ref` i `anyOf`, które obsługuje strict structured output w API zgodnym z OpenAI. Test pilnuje, że każdy obiekt w schemacie jest strict.
