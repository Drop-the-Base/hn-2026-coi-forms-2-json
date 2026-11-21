# ADR-0022: Serwer ASGI `uvicorn` i `python-multipart` dla uploadu

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-T3, FR-05, NFR-06

## Kontekst

[ADR-0002](0002-python-fastapi.md) wybrał FastAPI, ale FastAPI potrzebuje serwera ASGI, żeby przyjmować żądania, i biblioteki `python-multipart`, żeby przyjąć plik jako `UploadFile` (formularz multipart).

## Decyzja

- **`uvicorn`** (BSD-3) bez dodatku `[standard]`. Zależności przechodnie: `click` (BSD-3), `h11` (MIT). Uruchomienie: `uv run uvicorn forms2json.bootstrap:create_api --factory`.
- **`python-multipart`** (Apache-2.0), bez zależności. Wymagana przez FastAPI do `UploadFile`.
- Wszystkie licencje dozwolone przez [ADR-0013](0013-polityka-licencji.md).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `uvicorn[standard]` | `uvloop`, `httptools`, `watchfiles`: szybciej, ale więcej natywnych kół na Pythona 3.14, a wydajność serwera nie jest wąskim gardłem (LLM trwa minuty) |
| `hypercorn` (MIT) | mniej przykładów, HTTP/2 niepotrzebne |
| `granian` (BSD-3) | rdzeń w Ruście, młodszy projekt |
| surowe body (`application/octet-stream`) zamiast multipart | nazwa pliku w nagłówku zamiast w formularzu, mniej typowe dla frontendu i OpenAPI |

## Konsekwencje

- Starlette buforuje plik z formularza w `SpooledTemporaryFile`: powyżej 1 MB zapisuje go w katalogu tymczasowym (`TMPDIR`, domyślnie `/tmp`). Żeby plik nie trafił na dysk (NFR-06), kontener `api` musi mieć `/tmp` jako `tmpfs` albo `TMPDIR` wskazujący na wolumen tmpfs.
- Starlette nie ogranicza rozmiaru całego żądania. API czyta z pliku najwyżej `MAX_UPLOAD_BYTES + 1` bajtów, ale samo przyjęcie dużego żądania trzeba ograniczyć przed API (limit `tmpfs` albo reverse proxy).
