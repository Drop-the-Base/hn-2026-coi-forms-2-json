# ADR-0028: Model wymienny: open source u organizatorów, development na modelu open-weights w chmurze

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: NFR-03, NFR-13, NFR-16

## Kontekst

Ustalenie Benka z organizatorami: najważniejsza jest dokładność, koszt jest drugorzędny. Organizatorzy sami postawią model open source. Laptop zespołu nie uciągnie dużego modelu, więc development i ewaluacje muszą iść na większym modelu open-weights hostowanym w chmurze, przez API zgodne z OpenAI.

[ADR-0018](0018-klient-llm-openai-sdk.md) zakładał stały klucz `local` i zawsze `response_format` typu `json_schema` (strict). Dostawcy w chmurze wymagają klucza, a nie każdy wspiera strict `json_schema`.

## Decyzja

- Model jest wymienny: dowolny endpoint zgodny z OpenAI, wybór przez `LLM_BASE_URL` i `LLM_MODEL` (bez zmian w kodzie, NFR-16).
- Wdrożenie: model open source hostowany przez organizatorów. Development i ewaluacje: model open-weights u dostawcy w chmurze.
- Tylko modele z licencją zgodną z [ADR-0013](0013-polityka-licencji.md), np. gpt-oss (Apache-2.0), Qwen3 (Apache-2.0), DeepSeek (MIT). Licencję sprawdzamy dla każdego modelu osobno.
- Do chmury wysyłamy tylko dokumenty z publicznego katalogu `data/`.
- `LLM_API_KEY` (pydantic `SecretStr`, domyślnie `local` dla Ollamy) trafia do nagłówka `Authorization`. Sekret podajemy tylko przez zmienną środowiskową, nigdy nie logujemy.
- `LLM_RESPONSE_FORMAT`: `json_schema` (domyślnie, strict) albo `json_object`. W trybie `json_object` adapter dopisuje schemat do wiadomości systemowej, bo ten tryb gwarantuje tylko poprawny JSON. Walidacja pydantic w kroku Understand zostaje bez zmian.

To uzupełnia ADR-0018 w punkcie o kluczu API i ADR-0007 w punkcie o miejscu działania modelu.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Tylko lokalny mały model (Ollama na laptopie) | za mała dokładność, a dokładność jest priorytetem |
| Modele zamknięte dostępne tylko przez API | NFR-03 i ADR-0013: tylko modele open source |
| Tylko `json_schema` strict | część dostawców go nie wspiera albo odrzuca słowa kluczowe schematu |
| Tool calling zamiast `response_format` | wsparcie u dostawców równie nierówne, więcej kodu |

## Konsekwencje

- Zmiana dostawcy to zmiana czterech zmiennych w `.env`, bez zmian w kodzie.
- W trybie `json_object` model może nie dotrzymać schematu; łapie to walidacja pydantic i ponowienia w Understand.
- Klucz dostawcy w chmurze jest sekretem: tylko w `.env` (poza repo) i w zmiennych środowiskowych.
- Wyniki ewaluacji na modelu w chmurze mogą się różnić od modelu u organizatorów; przed oddaniem uruchamiamy evale na modelu docelowym, gdy będzie dostępny.
