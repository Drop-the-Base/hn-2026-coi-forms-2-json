# ADR-0012: Obraz workera: `python:3.14-slim` zamiast Alpine

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: NFR-07, NFR-01 (konflikt K-04)

## Kontekst

Wymagania preferują lekkie dystrybucje, np. Alpine. Worker potrzebuje bibliotek z kodem natywnym (OCR, przetwarzanie obrazów, czytniki PDF) i LibreOffice do konwersji `.doc`. Alpine używa musl, więc wiele pakietów nie ma gotowych wheeli i trzeba je kompilować.

## Decyzja

| Usługa | Obraz bazowy |
|---|---|
| `worker` | oficjalny `python:3.14-slim` (Debian), wersja przypięta co do tagu i digestu |
| `api` | oficjalny `python:3.14-alpine`, jeśli wszystkie zależności API mają wheele musl; inaczej `slim` |
| `frontend` | `nginxinc/nginx-unprivileged` w wersji Alpine |
| Pozostałe | oficjalne obrazy projektów, przypięte wersje, bez `latest` |

Wszystkie obrazy: build wieloetapowy, użytkownik bez roota, tylko porty niezbędne do działania.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Alpine dla workera | kompilacja zależności natywnych, dłuższe buildy, ryzyko różnic w zachowaniu |
| Distroless | brak oficjalnego obrazu dla Pythona 3.14 od dostawcy, trudniejsze debugowanie |

## Konsekwencje

Obraz workera jest większy. `api` też stoi na `slim` (przypadek „inaczej" z tabeli): koła musllinux `pypdfium2` (zależność `pdfplumber`, ADR-0023) zawierają kod na licencji GPL, a koła manylinux nie (ADR-0013). Odstępstwo od preferencji Alpine opisujemy w README z uzasadnieniem.
