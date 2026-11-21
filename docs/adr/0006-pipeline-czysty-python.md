# ADR-0006: Pipeline w czystym Pythonie, bez frameworka orkiestracji

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-12, NFR-16, NFR-02, NFR-11

## Kontekst

Pipeline ma 4 kroki wykonywane po kolei: Ingest → Understand → Compose → Validate ([architecture.md §4](../architecture.md#4-pipeline-w-workerze)). Musi być czytelny dla człowieka i łatwy do testowania krok po kroku.

## Decyzja

Czysty Python:
- `PipelineStep` (ABC) z metodą `run(input) -> output` na typach domenowych;
- `Pipeline` to lista kroków wywoływanych w pętli, każdy w spanie OTel;
- kroki dostają porty (np. `LlmClient`) przez konstruktor.

Cały przebieg da się przeczytać w jednym pliku definicji pipeline'u.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| LangChain / LangGraph | duża powierzchnia API, częste zmiany, ukrywa przepływ danych; vendor lock-in na abstrakcje frameworka |
| LlamaIndex | nastawiony na RAG, którego nie robimy |
| Haystack | sensowny, ale cięższy niż 4 kroki liniowe |
| Prefect / Dagster / Airflow | orkiestracja zadań wsadowych, za ciężkie dla jednego żądania |
| DSPy | ciekawe do optymalizacji promptów; w łańcuchu zależności był skompromitowany LiteLLM (patrz [ADR-0008](0008-bramka-llm.md)) |

## Konsekwencje

- Retry, timeouty i równoległość piszemy sami. Robimy to tylko tam, gdzie są potrzebne (np. retry na wywołaniu LLM).
- Gdy pipeline przestanie być liniowy (np. pętla poprawek przez LLM), wracamy do decyzji nowym ADR-em.
