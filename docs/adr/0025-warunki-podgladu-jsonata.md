# ADR-0025: Warunki `states` w podglądzie formularza: biblioteka `jsonata`

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-E5, FR-E3, NFR-15

## Kontekst

Podgląd formularza (FR-E5, issue #53) ma pokazywać formularz tak, jak zobaczy go wnioskodawca, w tym stany dynamiczne pól i sekcji (`states`: `SHOW`, `READ_ONLY`). Warunki są wyrażeniami JSONata, np. `"Innej osoby" in tabs['Dane' in title]…field.__userAnswer`. Bez ich obliczania podgląd pokazuje naraz wszystkie warianty formularza (wzorzec 1 ma ich kilkanaście), więc nie da się go porównać z wizualizacjami COI.

## Decyzja

Oficjalna biblioteka [`jsonata`](https://github.com/jsonata-js/jsonata) (licencja **MIT**, sprawdzona na npm i w pliku `LICENSE`, bez zależności runtime), w przeglądarce. Dokumentacja (Context7, `/jsonata-js/jsonata`) potwierdza działanie w przeglądarce; `evaluate()` zwraca `Promise`.

- Podgląd trzyma lokalne odpowiedzi (`useState`), wstawia je jako `field.__userAnswer` do kopii JSON-a i liczy każdy warunek. Odpowiedzi nie trafiają do pobieranego JSON-a.
- `SHOW`: pole widoczne, gdy wszystkie warunki `SHOW` są prawdziwe. `READ_ONLY`: tylko do odczytu, gdy któryś warunek jest prawdziwy.
- Warunek, który się nie kompiluje albo rzuca błąd, nie ukrywa pola: pole zostaje widoczne z ostrzeżeniem i treścią warunku.
- Biblioteka i wzorce ładują się leniwie razem z trasą podglądu, poza głównym pakietem.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Pokazać wszystko i oznaczyć warunek ikoną | prostsze, ale podgląd nie wygląda jak formularz po wyborze opcji; nie da się sprawdzić, czy warunki działają (FR-E3) |
| Własny parser podzbioru JSONata (`"X" in …`, `$not`) | kruche przy każdym nowym wzorcu zapytania, więcej kodu niż jedna zależność |
| Ewaluacja w backendzie | dodatkowy endpoint i opóźnienie przy każdym kliknięciu, YAGNI |

## Konsekwencje

- Ok. 40 kB gzip w osobnym chunku trasy podglądu.
- Ta sama biblioteka może posłużyć w walidatorze (FR-08) do sprawdzania składni warunków, jeśli backend dostanie odpowiednik (`jsonata-python` wymaga osobnego ADR).
