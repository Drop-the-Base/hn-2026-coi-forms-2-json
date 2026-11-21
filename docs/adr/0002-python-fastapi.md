# ADR-0002: Backend: Python 3.14 + FastAPI

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-01, FR-01, FR-10, NFR-09

## Kontekst

Zadanie dopuszcza Java 21+ albo Python 3.14+. Ekosystem do dokumentów, OCR i lokalnych modeli jest najbogatszy w Pythonie. API musi przyjmować plik, mieć JWT i dokumentację REST.

## Decyzja

Python 3.14 + FastAPI (licencja MIT). Modele żądań i odpowiedzi w pydantic v2. OpenAPI generowane automatycznie służy za opis REST API w README i za źródło typów dla frontendu.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Java 21 + Spring Boot | słabszy ekosystem OCR i lokalnych LLM, wolniejsze iteracje na hackathonie |
| Litestar | mniejsza społeczność, mniej przykładów dla agentów |
| Flask | brak natywnego async i walidacji, więcej kodu ręcznego |

## Konsekwencje

- Python 3.14 jest nowy: każda zależność musi mieć wheel na 3.14. Sprawdzamy to przy dodawaniu zależności.
- Uploady duże i wolne: używamy `UploadFile` i limitu rozmiaru sprawdzanego przed wczytaniem całego pliku.
