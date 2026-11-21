# ADR-0021: Kolejka zadań: `aio-pika` za portem `JobQueue`

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: NFR-02, NFR-06, FR-T5

## Kontekst

[ADR-0004](0004-przetwarzanie-asynchroniczne-rabbitmq.md) wybrał RabbitMQ i wspomniał klienta `aio-pika`. Ten ADR dodaje go do zależności, sprawdza licencje całego drzewa i ustala, jak klient async współpracuje z synchronicznym pipeline'em.

## Decyzja

- **`aio-pika`** (Apache-2.0) za portem `JobQueue` (ABC, metody `async`). API jest w FastAPI (async), więc jeden klient async obsłuży api i workera.
- Zależności przechodnie: `aiormq` (Apache-2.0), `pamqp` (BSD-3), `yarl` (Apache-2.0), `multidict` (Apache-2.0), `propcache` (Apache-2.0), `idna` (BSD-3). Wszystkie dozwolone przez [ADR-0013](0013-polityka-licencji.md).
- Topologia: kolejki `jobs` i `results` (domyślny exchange), exchange `progress` typu topic z kluczem `job_id` ([ADR-0014](0014-sse-postep-pipeline.md)). Nic nie jest `durable`, wiadomości mają `delivery_mode=1`, JSON. W zadaniu są tylko `job_id` (UUID) i `mime_type`, plik leży w `FileStore`.
- `connect_robust`: po zerwaniu połączenia klient sam wraca i odtwarza kolejki i konsumentów.
- Worker: `prefetch_count=1`, ack po zakończeniu `ProcessJob`. Zabity worker zostawia zadanie dla innego, a plik czeka na sprzątacza TTL. Wiadomość, która nie przechodzi walidacji pydantikiem, jest odrzucana bez ponowienia.
- Pipeline jest synchroniczny ([ADR-0006](0006-pipeline-czysty-python.md)), więc `ProcessJob` uruchamia go przez `asyncio.to_thread`. Pętla zdarzeń zostaje wolna dla heartbeatów AMQP podczas długich wywołań LLM.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `pika` (BSD-3) | synchroniczny, w FastAPI wymagałby osobnego wątku na połączenie |
| `aiormq` bezpośrednio | niskopoziomowy, bez automatycznego wznawiania połączenia |
| `faststream` (Apache-2.0) | framework z własnym routingiem i DI, za dużo jak na dwie kolejki i exchange |

## Konsekwencje

- Testy jednostkowe `ProcessJob` używają `FakeJobQueue` i `asyncio.run`, bez `pytest-asyncio`.
- Test integracyjny (`-m integration`) wymaga działającego RabbitMQ pod `RABBITMQ_URL`.
- Wiadomość z błędem zawiera tylko typ wyjątku, bo komunikaty parserów mogą cytować treść dokumentu. Szczegóły są w logu workera.
