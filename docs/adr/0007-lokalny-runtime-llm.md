# ADR-0007: Lokalny runtime LLM: Ollama, API zgodne z OpenAI

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: NFR-03, NFR-04, NFR-13, NFR-16

## Kontekst

Rozwiązanie nie może używać LLM dostępnych tylko przez API (Z 5). Modele muszą działać lokalnie w kontenerze. Koszt wdrożenia to 20% oceny, więc preferujemy małe modele, które da się uruchomić bez GPU. Dokumenty są po polsku.

## Decyzja

- Osobny kontener `llm-runtime` z **Ollama** (MIT), który wystawia API zgodne z OpenAI.
- Worker mówi z modelem tylko przez bramkę ([ADR-0008](0008-bramka-llm.md)) i port `LlmClient`. Adapter używa klienta `openai` (Apache-2.0) z `base_url` bramki.
- Model wybieramy na podstawie evali ([ADR-0010](0010-ewaluacje-pytest.md)). Kandydaci z licencją Apache-2.0: **Bielik** (polski) i **Qwen** (rodzina z dobrym wyjściem strukturalnym, także wersje VL do obrazów). Wybór zapisujemy w osobnym ADR.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| vLLM (Apache-2.0) | wymaga GPU, cięższy obraz; zamiennik w produkcji z GPU, ten sam interfejs OpenAI |
| llama.cpp server (MIT) | lżejszy niż Ollama, ale mniej wygodne zarządzanie modelami; zamiennik bez zmian w kodzie |
| Modele Llama | licencja Llama Community nie jest licencją open source (NFR-02) |
| Modele Gemma | własne warunki użytkowania Google, nie OSI (NFR-02) |
| API OpenAI / Anthropic / Gemini | zakazane w działającym rozwiązaniu (NFR-03) |

## Konsekwencje

- Wagi modeli są duże: nie wkładamy ich do obrazu, tylko pobieramy do wolumenu przy pierwszym uruchomieniu (opis w README).
- Każdy runtime z API OpenAI da się podstawić zmianą konfiguracji bramki.
