# ADR-0030: Dashboard kosztów w Perses, stawki za tokeny wejścia i wyjścia

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-13, NFR-14, NFR-02

## Kontekst

[ADR-0009](0009-obserwowalnosc-opentelemetry.md) zostawił Perses jako opcję, gdyby na demo był potrzebny dashboard kosztów. Benek chce go widzieć (koszt na wywołanie i na zadanie, tokeny, czasy, błędy). Frontend jest tylko dla urzędnika, więc dashboard nie trafia do aplikacji. Dostawcy w chmurze ([ADR-0028](0028-model-wymienny-open-source-w-chmurze.md)) liczą osobno tokeny wejścia i wyjścia, więc jedna stawka `COST_PER_1K_TOKENS` zaniżała albo zawyżała koszt.

## Decyzja

- **Perses** (`persesdev/perses`, Apache-2.0, projekt CNCF) w profilu `observability`, port tylko `127.0.0.1:8081`.
- Dashboard jako kod: `deploy/perses/resources/` (projekt, datasource Prometheus, dashboard), wczytywany przez provisioning. Baza Perses w tmpfs, API w trybie `readonly`: zmiana dashboardu = zmiana pliku w repo.
- Stawki: `COST_PER_1M_INPUT_TOKENS`, `COST_PER_1M_OUTPUT_TOKENS`, `COST_PER_GPU_SECOND` (model lokalny), `COST_CURRENCY`. Domyślnie 0. `COST_PER_1K_TOKENS` usunięte.
- Koszt liczy `CostRates` w domenie. Wynik zadania ma `usage.cost` i `usage.currency`; metryka `forms2json_job_cost` bierze koszt z wyniku. Adapter LLM zapisuje koszt każdego wywołania osobno dla wejścia i wyjścia (`forms2json_llm_call_cost`) i licznik błędów `forms2json_llm_errors_total{error_type}`.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Grafana | AGPL-3.0, zakaz NFR-02 ([ADR-0013](0013-polityka-licencji.md)) |
| Dashboard we frontendzie | front jest dla urzędnika, nie dla zespołu; duplikowałby Prometheusa |
| Tylko UI Prometheusa | brak zapisanego widoku, każde zapytanie trzeba wpisać ręcznie |
| Koszt liczony w PromQL (tokeny × stawka) | stawki musiałyby żyć w dashboardzie; `usage.cost` w wyniku i tak jest potrzebny |

## Konsekwencje

- Jedna usługa więcej w profilu `observability`; bez profilu aplikacja działa jak dotąd.
- Zapytania używają wartości skumulowanych od startu workera, nie `rate()`: dashboard pokazuje dane już po jednym zadaniu, ale restart workera zeruje sumy.
- Stawki dostawcy trzeba sprawdzić w jego cenniku; repo ma domyślnie 0.

## Dopisek: zasoby kontenerów (#148)

- Sekcja „Zasoby” (RAM i CPU per usługa compose, RAM łącznie) z receivera `docker_stats`. Wymaga dystrybucji `otel/opentelemetry-collector-contrib` (Apache-2.0, ta sama wersja co core).
- **Kompromis bezpieczeństwa**: otel-collector dostaje `/var/run/docker.sock` tylko do odczytu. `:ro` blokuje zapis do pliku, nie do API: kto przejmie Collector, może sterować Dockerem, czyli w praktyce ma roota na hoście. Socket Docker Desktop jest `root:root 0660`, więc Collector dostaje `group_add: ["0"]` (grupa root), a nie `user: "0"`; zostaje użytkownik 10001, `read_only`, `cap_drop: [ALL]`, `no-new-privileges`. Akceptowalne lokalnie i na demo; w produkcji zamiast socketu metryki z kubeleta (`kubeletstats`) albo cAdvisora.
- Collector nie wystawia portów na zewnątrz, a jedyne wejście to OTLP z sieci compose.

