# ADR-0024: Tracing OTel w `api` i `worker`: pakiety i propagacja przez RabbitMQ

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: NFR-14, NFR-02

## Kontekst

[ADR-0009](0009-obserwowalnosc-opentelemetry.md) wybrał OpenTelemetry, Collector i Jaegera, ale bez konkretnych pakietów Pythona. Chcemy jednego trace'a od żądania HTTP przez kolejkę do kroków pipeline'u i wywołań LLM. Domena i warstwa application nie mogą importować OTel ([ADR-0003](0003-architektura-heksagonalna-abc.md)).

## Decyzja

- Pakiety (bezpośrednie): `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` (Apache-2.0), `opentelemetry-instrumentation-fastapi` (Apache-2.0).
- Zależności przechodnie: pozostałe `opentelemetry-*` (Apache-2.0), `protobuf` (BSD-3), `googleapis-common-protos` (Apache-2.0), `requests` (Apache-2.0), `urllib3` (MIT), `charset-normalizer` (MIT), `asgiref` (BSD-3), `wrapt` (BSD-2), `certifi` (MPL-2.0, wyjątek warunkowy w [ADR-0013](0013-polityka-licencji.md)).
- Konfiguracja w `bootstrap.py` (`configure_tracing`): `service.name` = `api` albo `worker`, eksport OTLP/HTTP tylko gdy ustawiono `OTEL_EXPORTER_OTLP_ENDPOINT`. Bez tej zmiennej API OTel jest no-opem i aplikacja działa jak wcześniej. Pozostałe ustawienia eksportera czyta on sam ze standardowych zmiennych `OTEL_EXPORTER_OTLP_*`.
- Propagacja przez RabbitMQ ręcznie w `RabbitMqJobQueue`: `propagate.inject` do nagłówków wiadomości przy publikacji, `propagate.extract` przy odbiorze i span `process <kolejka>` (`CONSUMER`). Wiadomość bez kontekstu (zdarzenia postępu z wątku pipeline'u) nie dostaje spanu, żeby nie tworzyć osobnego trace'a na każde zdarzenie.
- Span per krok pipeline'u: adapter `TracingObserver` (port `PipelineObserver`). Wyjątek w kroku ustawia status `ERROR` (domyślne zachowanie `start_as_current_span`). `asyncio.to_thread` kopiuje kontekst, więc kroki są dziećmi spanu `process jobs`.
- Span per wywołanie LLM w `OpenAiCompatibleLlmClient`: `chat <model>` (`CLIENT`) z atrybutami konwencji GenAI: `gen_ai.operation.name`, `gen_ai.provider.name` (`openai`, czyli rodzaj API), `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `opentelemetry-instrumentation-aio-pika` | dodatkowa zależność i własne spany publish/consume dla każdej wiadomości (także postępu), a propagacja to kilka linii |
| `opentelemetry-exporter-otlp-proto-grpc` | ciągnie `grpcio` (duże koła natywne); OTLP/HTTP na porcie 4318 wystarczy |
| `opentelemetry-distro` i auto-instrumentacja (`opentelemetry-instrument`) | magia przy starcie procesu, trudniej testować; jawna konfiguracja w composition root jest krótka |
| instrumentacja `openai`/`httpx` | span HTTP pod spanem LLM nic nie dodaje; tokeny i tak bierzemy z naszego `LlmUsage` |

## Konsekwencje

- Metryki (#40) nie wymagają nowych pakietów: `opentelemetry-sdk` ma `MeterProvider`, a `opentelemetry-exporter-otlp-proto-http` eksporter metryk. `configure_telemetry` włącza je razem z tracingiem (ten sam warunek `OTEL_EXPORTER_OTLP_ENDPOINT`). Adaptery: `MetricsObserver` (czas kroków, port `PipelineObserver`), `JobMetrics` (czas, wynik, koszt i confidence zadania, port `JobObserver`), histogram `gen_ai.client.token.usage` w `OpenAiCompatibleLlmClient`.
- Metryki z trace'ów dla zakładki Monitor liczy konektor `span_metrics` w Jaegerze v2 (`deploy/jaeger.yaml`), bo obraz rdzenia otel-collectora go nie ma; dzięki temu nie zmieniamy obrazu Collectora na `contrib`.
- Span LLM, który się nie powiódł, ma status błędu, ale nie ma atrybutów `gen_ai.usage.*`.
- Testy jednostkowe używają `InMemorySpanExporter`; globalny `TracerProvider` w procesie testów ustawia tylko `tests/unit/test_tracing.py`.
