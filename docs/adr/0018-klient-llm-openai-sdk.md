# ADR-0018: Klient LLM: SDK `openai` z własną pętlą ponowień

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-03, NFR-13, NFR-16

## Kontekst

[ADR-0007](0007-lokalny-runtime-llm.md) ustala, że adapter `LlmClient` mówi z lokalnym runtime'em (Ollama) przez API zgodne z OpenAI. Potrzebujemy klienta HTTP, wyjścia strukturalnego (`response_format` z JSON Schema), timeoutu, ograniczonych ponowień i liczby tokenów z odpowiedzi (NFR-13).

## Decyzja

- Adapter `OpenAiCompatibleLlmClient` używa SDK **`openai`** (Apache-2.0) z `base_url` z konfiguracji (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`). Klucz API to stała `local`: runtime lokalny go nie sprawdza, a SDK go wymaga (NFR-03: żadnych kluczy zewnętrznych dostawców).
- Wbudowane ponowienia SDK są wyłączone (`max_retries=0`). Adapter ma jedną pętlę (3 próby), która ponawia błędy sieci, timeout i odpowiedź, która nie jest obiektem JSON. Błąd 4xx/5xx od runtime'u nie jest ponawiany. Po wyczerpaniu prób adapter rzuca `LlmCallFailed`.
- Tokeny i czas są sumowane po wszystkich próbach i zwracane w `LlmUsage`. Atrybuty OTel `gen_ai.usage.*` dopisze #39.

Licencje (sprawdzone w metadanych pakietów): `openai` Apache-2.0, `httpx2` i `httpcore2` BSD-3-Clause, `anyio`, `h11`, `jiter`, `truststore` MIT, `sniffio` MIT OR Apache-2.0, `idna` BSD-3-Clause. Bez wyjątków z [ADR-0013](0013-polityka-licencji.md).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `urllib.request` (stdlib) | trzeba ręcznie pisać timeouty, mapowanie błędów i modele odpowiedzi; ADR-0007 wskazał już SDK `openai` |
| `httpx` bezpośrednio | to samo co wyżej, a SDK i tak go (w wersji `httpx2`) dociąga |
| Ponowienia SDK + osobna pętla dla złego JSON-a | dwie pętle, mnożenie prób i wolne testy przez backoff SDK |
| Klient `ollama` | wiąże nas z jednym runtime'em, a vLLM i llama.cpp mówią API OpenAI (NFR-16) |

## Konsekwencje

- Zmiana runtime'u (vLLM, llama.cpp) to zmiana `LLM_BASE_URL` i `LLM_MODEL`, bez zmian w kodzie.
- Adapter sprawdza tylko, że odpowiedź to obiekt JSON. Zgodność ze schematem waliduje wywołujący swoim modelem pydantic (coding-rules §2.4).
- Ollama przekazuje schemat do silnika bez walidacji słów kluczowych; mały model może go nie dotrzymać, stąd walidacja po stronie wywołującego.
