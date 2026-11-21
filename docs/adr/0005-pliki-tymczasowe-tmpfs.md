# ADR-0005: Pliki tymczasowe na współdzielonym tmpfs

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-06, FR-05

## Kontekst

Wymaganie: plik wolno przetwarzać tylko w pamięci albo w przestrzeni tymczasowej na czas realizacji żądania (konflikt K-02). API i worker to osobne kontenery, więc plik musi między nimi przejść.

## Decyzja

- Nazwany wolumen Docker typu `tmpfs` (RAM) montowany w `api` i `worker` pod `/jobs`.
- `api` zapisuje plik jako `/jobs/{job_id}/{bezpieczna_nazwa}`, a w wiadomości wysyła tylko ścieżkę i metadane.
- `worker` usuwa katalog zadania w `finally` po zakończeniu przetwarzania.
- Sprzątacz w `api` usuwa katalogi starsze niż `FILE_TTL_SECONDS` (zadania przerwane awarią).
- Rozmiar wolumenu ograniczony (`size=`) do `MAX_FILE_SIZE × MAX_CONCURRENT_JOBS` z zapasem.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Plik w treści wiadomości RabbitMQ | duże wiadomości (obrazy kilkanaście MB) obciążają broker, broker może zrzucić je na dysk przy braku pamięci |
| MinIO / S3 | trwały magazyn, sprzeczny z NFR-06, kolejna usługa |
| Zwykły wolumen na dysku | plik ląduje na dysku hosta |

## Konsekwencje

- `api` i `worker` muszą działać na tym samym hoście. Na hackathon to w porządku. `# shortcut: shared tmpfs needs one host; pass bytes in the message or use encrypted object storage with TTL when going multi-host`.
- Zadanie asynchroniczne może trwać dłużej niż samo żądanie HTTP. Plik żyje do końca przetwarzania zadania, nie dłużej. Opisujemy to w README jako interpretację wymagania.
