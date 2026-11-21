# ADR-0017: Odczyt arkuszy: openpyxl dla XLSX, biblioteka standardowa dla ODS

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-02, NFR-02, NFR-05

## Kontekst

Krok Ingest musi czytać formularze w XLSX i ODS (FR-02) do `NormalizedDocument`. Formularze w `data/` są rysowane na gęstej siatce (do ~130 kolumn), z wieloma scalonymi komórkami, bez formuł istotnych dla treści.

## Decyzja

- **XLSX: `openpyxl`** (MIT; zależność przechodnia `et-xmlfile`, MIT). Tryb `read_only=True, data_only=True`: tylko wartości, bez ładowania stylów i bez liczenia formuł. Stuby typów `types-openpyxl` (Apache-2.0) w grupie dev, dla `mypy --strict`.
- **ODS: `zipfile` + `xml.etree.ElementTree` z biblioteki standardowej.** Potrzebujemy tylko tekstu komórek z `content.xml`: `table:table` → `table:table-row` → `table:table-cell` → `text:p`, plus atrybuty powtórzeń. To około 50 linii kodu.

Wspólny kształt wyniku: arkusz = strona, na stronie jedna `Table`, w wierszu tylko niepuste komórki w kolejności kolumn. Wartość scalonej komórki występuje raz (lewy górny róg). Na danych z `data/` oba adaptery dają identyczny wynik dla par XLSX/ODS tego samego formularza.

Powtórzenia w ODS (`number-rows-repeated`, `number-columns-repeated`, `text:c`) są ograniczone do 100, bo mały plik może zadeklarować milion powtórzeń. Puste powtórzone wiersze są pomijane bez rozwijania.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| pandas (`read_excel`, silnik `odf`) | ciężka zależność (numpy), gubi informację o scaleniach, ODS i tak przez `odfpy` |
| odfpy | trójlicencja Apache-2.0/GPL/LGPL, wolne, niskopoziomowe API i tak wymaga obsługi powtórzeń |
| pyexcel-ods3 / ezodf | słabo utrzymywane, kolejne zależności dla prostego XML-a |
| konwersja ODS → XLSX przez LibreOffice | proces zewnętrzny i sekundy na plik zamiast milisekund |
| python-calamine | binarne wiązania do Rusta, nie potrzebujemy tej wydajności |
| defusedxml dla ODS | `expat` w Pythonie 3.14 ma ochronę przed „billion laughs”, a `ElementTree` nie pobiera encji zewnętrznych |

## Konsekwencje

- Jedna nowa zależność runtime (`openpyxl`) i jedna dev (`types-openpyxl`).
- Kod ODS jest nasz: przy nowych elementach tekstu (np. hiperłącza `text:a`) tekst i tak jest zbierany rekurencyjnie, ale specjalne elementy trzeba dopisać ręcznie.
- Rozmiar pliku ogranicza walidacja przy wgrywaniu (`domain/upload.py`).
