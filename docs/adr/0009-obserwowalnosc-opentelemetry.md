# ADR-0009: Obserwowalność: OTel Collector + Jaeger + Prometheus, bez Grafany

- Status: Zaakceptowana (2026-11-21, K-03 zamknięty: bez Grafany)
- Data: 2026-11-21
- Wymagania: NFR-14, NFR-13, NFR-02

## Kontekst

Chcemy widzieć każde żądanie od uploadu do wyniku: latencję per krok, wywołania LLM, tokeny, koszt, błędy, confidence. Stos ma być standardowy, w klasie „enterprise", ale lekki. Ograniczenie: zakaz licencji copyleft (NFR-02).

## Decyzja

| Element | Narzędzie | Licencja |
|---|---|---|
| Instrumentacja | OpenTelemetry SDK (Python, JS), instrumentacje FastAPI, aio-pika, httpx, OpenAI; konwencje GenAI (`gen_ai.usage.*` dla tokenów) | Apache-2.0 |
| Zbieranie | OpenTelemetry Collector | Apache-2.0 |
| Traces | Jaeger v2 | Apache-2.0 |
| Metryki | Prometheus | Apache-2.0 |
| Widoki | Jaeger, zakładka Monitor (SPM): latencja, liczba żądań i błędy per endpoint z metryk Prometheusa; UI Prometheusa dla tokenów i kosztu | Apache-2.0 |
| Dashboardy (opcjonalnie) | **Perses**, tylko jeśli na demo potrzebny dashboard kosztów; dashboardy jako kod w repo | Apache-2.0 |

Pakiety Pythona i propagacja kontekstu: [ADR-0024](0024-tracing-otel-pakiety.md).

Aplikacja zależy tylko od OTLP. Backend obserwowalności to wymienny element infrastruktury.

Grafany nie używamy: AGPL jest wprost wymieniona w zakazie (NFR-02), a SPM w Jaegerze pokrywa podstawowe metryki bez dodatkowej usługi.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Grafana, Tempo, Loki | AGPL-3.0 (NFR-02) |
| Langfuse | self-hosting wymaga Postgres + ClickHouse + Redis + S3, za ciężki; część funkcji w `ee/` |
| Arize Phoenix | licencja Elastic License 2.0, nie open source (NFR-02); w łańcuchu zależności był skompromitowany LiteLLM |
| SigNoz | ClickHouse, cięższy niż Jaeger + Prometheus |
| OpenObserve | AGPL-3.0 |

## Konsekwencje

- Koszt liczymy modeli lokalnych ze stawki konfiguracyjnej (`COST_PER_1K_TOKENS` / `COST_PER_GPU_SECOND`), bo nie ma faktury.
- Bez profilu `observability` aplikacja działa normalnie, a Collector może eksportować do logów.
