# ADR-0004: RabbitMQ + worker, tryb sync i async

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: FR-01, FR-06, FR-T3, FR-E6, NFR-06

## Kontekst

Przetwarzanie (konwersja DOC, OCR, LLM) trwa od kilku sekund do minut. Trzymanie tego w procesie HTTP blokuje API i utrudnia batch. Jednocześnie zadanie mówi: „w odpowiedzi aplikacja zwraca dokument JSON" (K-01: to nie konflikt w wymaganiach, tylko skutek wyboru kolejki).

## Decyzja

- `api` publikuje zadanie do kolejki `jobs` w RabbitMQ. `worker` je konsumuje i publikuje wynik do `results`. `api` konsumuje wyniki i trzyma je w pamięci z TTL (port `ResultStore`).
- Dwa endpointy:
  - `POST /api/v1/forms:convert`: czeka na wynik do `SYNC_TIMEOUT_SECONDS` i zwraca JSON (spełnia FR-01/FR-06). Po przekroczeniu limitu zwraca `202` z `job_id`.
  - `POST /api/v1/jobs` → `202` + `job_id`, `GET /api/v1/jobs/{id}` → status i wynik. Dla frontendu i batcha.
- Kolejki nietrwałe, wiadomości z `delivery_mode=1`. RabbitMQ 3.12+ i tak może odłożyć wiadomość na dysk, dlatego w wiadomości są tylko ścieżka i metadane, nigdy bajty pliku (NFR-06, [ADR-0005](0005-pliki-tymczasowe-tmpfs.md)).
- Klient Pythona: `aio-pika` (Apache-2.0).
- Kontekst OTel jest przekazywany w nagłówkach wiadomości, więc trace przechodzi przez API i workera.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Przetwarzanie w procesie API (`BackgroundTasks`) | blokuje workerów HTTP, brak skalowania i izolacji ciężkich zależności |
| Celery | ciężki, dużo konfiguracji, nie potrzebujemy harmonogramów ani retry policy |
| Redis jako broker | Redis 8 ma licencję AGPL/SSPL (NFR-02) |
| Valkey + RQ/arq | możliwe (BSD), ale RabbitMQ daje czytelny model kolejek i panel do debugowania; zostaje jako zamiennik |
| NATS JetStream | lekki (Apache-2.0), ale zespół zna RabbitMQ |

## Konsekwencje

- RabbitMQ ma licencję MPL-2.0 (słaby copyleft na poziomie plików). Używamy niezmodyfikowanego obrazu, więc nie mamy nic do publikowania. Opis w [ADR-0013](0013-polityka-licencji.md).
- Wyniki w pamięci API znikają przy restarcie. To zgodne z NFR-06 i wystarcza na hackathon. `# shortcut: in-memory ResultStore, one API replica only; move to Valkey when scaling API`.
