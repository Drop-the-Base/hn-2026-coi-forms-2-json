# ADR-0009: Obserwowalność: OTel Collector + Jaeger + Prometheus + Grafana (opcjonalnie)

- Status: Proponowana (Grafana czeka na odpowiedź mentorów, konflikt K-03)
- Data: 2026-11-21
- Wymagania: NFR-14, NFR-13, NFR-02

## Kontekst

Chcemy widzieć każde żądanie od uploadu do wyniku: latencję per krok, wywołania LLM, tokeny, koszt, błędy, confidence. Stos ma być standardowy, w klasie „enterprise", ale lekki. Ograniczenie: zakaz licencji copyleft (NFR-02).

## Decyzja

| Element | Narzędzie | Licencja |
|---|---|---|
| Instrumentacja | OpenTelemetry SDK (Python, JS), instrumentacje FastAPI, aio-pika, httpx, OpenAI; konwencje GenAI | Apache-2.0 |
| Zbieranie | OpenTelemetry Collector | Apache-2.0 |
| Traces | Jaeger v2 | Apache-2.0 |
| Metryki | Prometheus | Apache-2.0 |
| Dashboardy | **Grafana**, tylko w profilu `observability` | **AGPL-3.0** |

Aplikacja zależy tylko od OTLP. Backend obserwowalności to wymienny element infrastruktury.

Grafana nie jest biblioteką aplikacji, tylko osobnym, niezmodyfikowanym narzędziem uruchamianym opcjonalnie. Mimo to AGPL jest wprost wymieniona w zakazie, więc:
1. pytamy mentorów, czy Grafana jako opcjonalne narzędzie operacyjne jest dopuszczalna;
2. jeśli nie: zastępujemy ją **Perses** (Apache-2.0, projekt CNCF), który czyta z Prometheusa. Dashboardy trzymamy w repo jako kod.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Grafana Tempo / Loki | AGPL-3.0 |
| Langfuse | self-hosting wymaga Postgres + ClickHouse + Redis + S3, za ciężki; część funkcji w `ee/` |
| Arize Phoenix | licencja Elastic License 2.0, nie open source (NFR-02); w łańcuchu zależności był skompromitowany LiteLLM |
| SigNoz | ClickHouse, cięższy niż Jaeger + Prometheus |
| OpenObserve | AGPL-3.0 |

## Konsekwencje

- Dashboard kosztów liczy koszt modeli lokalnych ze stawki konfiguracyjnej (`COST_PER_1K_TOKENS` / `COST_PER_GPU_SECOND`), bo nie ma faktury.
- Bez profilu `observability` aplikacja działa normalnie, a Collector może eksportować do logów.
