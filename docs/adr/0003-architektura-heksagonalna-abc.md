# ADR-0003: Architektura heksagonalna, porty jako ABC

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-12, NFR-16, NFR-11

## Kontekst

Będziemy wymieniać dostawców: model LLM, silnik OCR, czytniki formatów, może broker. Zmiana dostawcy nie może ruszać logiki tworzenia formularza. Kod ma być czytelny dla jury.

## Decyzja

Porty i adaptery (hexagonal). Warstwy `domain` ← `application` ← `adapters`, struktura w [architecture.md §5](../architecture.md#5-architektura-heksagonalna-backend).

Porty to klasy `abc.ABC` z metodami `@abstractmethod`. Adaptery jawnie dziedziczą po porcie. `bootstrap.py` przy starcie instancjonuje wszystkie adaptery, więc adapter bez wymaganej metody rzuca `TypeError` przy uruchomieniu, a nie w trakcie żądania.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `typing.Protocol` | sprawdzany tylko statycznie przez mypy, nie wymusza kompletności w runtime |
| Kontener DI (np. `dependency-injector`) | dodatkowa zależność, ręczny composition root wystarcza przy kilkunastu adapterach |
| Architektura warstwowa bez portów | domena zależałaby od konkretnych bibliotek, wymiana modelu ruszałaby logikę |

## Konsekwencje

- Każdy port ma fałszywą implementację do testów (`Fake*`).
- Trochę więcej plików niż w prostym skrypcie. Pilnujemy, żeby portem był tylko styk z zewnętrznym światem (pliki, OCR, LLM, kolejka, magazyn), a nie każda klasa (YAGNI).
