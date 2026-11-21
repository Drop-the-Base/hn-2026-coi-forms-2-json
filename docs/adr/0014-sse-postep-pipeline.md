# ADR-0014: Postęp pipeline'u na żywo przez SSE

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-T5, FR-T3, NFR-14

## Kontekst

Przetwarzanie trwa od kilku sekund do minut. Urzędnik powinien widzieć, co się dzieje („Odczyt pliku… OCR strony 3/16… Analiza przez model… Walidacja: 2 ostrzeżenia"), a nie kręcące się kółko. Komunikacja jest jednokierunkowa: serwer → przeglądarka.

## Decyzja

- Worker publikuje zdarzenia postępu do exchange `progress` w RabbitMQ (topic, klucz = `job_id`), nietrwałe.
- Zdarzenie: `{job_id, step, status: started|progress|done|failed, message, progress?: 0..1, ts}`. Bez treści pliku i danych osobowych.
- API wystawia `GET /api/v1/jobs/{id}/events` jako **Server-Sent Events**. Używamy natywnego wsparcia FastAPI albo `sse-starlette` (BSD-3), co wybierzemy przy implementacji.
- Po zdarzeniu końcowym (`done`/`failed` całego zadania) strumień się zamyka. `GET /api/v1/jobs/{id}` zostaje jako zapasowy polling.
- Frontend: przeglądarkowy `EventSource` **nie wysyła nagłówka `Authorization`**, więc nie przekaże JWT. Używamy SSE przez `fetch` ze strumieniowaniem (`@microsoft/fetch-event-source`, MIT) i normalnym nagłówkiem `Authorization: Bearer`. Nie dajemy tokena w query stringu, bo trafia do logów.
- Hook `useJobEvents(jobId)` w `features/jobs` łączy zdarzenia SSE z cache TanStack Query.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Tylko polling | prostszy, ale opóźniony i bez szczegółów kroków; zostaje jako zapas |
| WebSocket | komunikacja dwukierunkowa niepotrzebna, trudniej przez proxy |
| Natywny `EventSource` + token w URL | token w logach serwera i proxy |
| Natywny `EventSource` + cookie | wymaga osobnego mechanizmu sesji i ochrony CSRF obok JWT |

## Konsekwencje

- nginx przed API musi mieć wyłączone buforowanie dla ścieżki SSE (`proxy_buffering off`).
- Zdarzenia postępu to te same granice kroków co spany OTel, więc obie rzeczy emituje jedno miejsce w `Pipeline`.
