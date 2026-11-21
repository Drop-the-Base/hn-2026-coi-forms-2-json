# ADR-0023: Odczyt PDF: pdfplumber

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-02, NFR-02, NFR-04

## Kontekst

Krok Ingest musi czytać formularze PDF z warstwą tekstową (FR-02) do `NormalizedDocument`: tekst w kolejności czytania na każdej stronie, tabele i pola wyboru. Formularze w `data/` to głównie PDF-y wyeksportowane z Worda, z ramkami rysowanymi liniami. PyMuPDF odpada przez AGPL ([ADR-0013](0013-polityka-licencji.md)). Skan bez warstwy tekstowej idzie do OCR (#25), więc reader musi go rozpoznać.

## Decyzja

**`pdfplumber`** (MIT). Daje znaki z pozycjami, linie tekstu (`extract_text_lines`) i tabele z linii ramek (`find_tables`), więc kolejność czytania i tabele to kilkanaście linii naszego kodu.

Zależności przechodnie (sprawdzone w metadanych paczek):

| Paczka | Licencja |
|---|---|
| pdfminer.six | MIT |
| pypdfium2 | Apache-2.0 / BSD-3-Clause (PDFium: BSD-3; dołączone biblioteki w kołach glibc: licencje permisywne) |
| Pillow | MIT-CMU (permisywna, odmiana HPND) |
| charset-normalizer | MIT |
| cryptography | Apache-2.0 OR BSD-3-Clause |
| cffi | MIT-0 |
| pycparser | BSD-3-Clause |

Koła `pypdfium2` dla musl dołączają `libgcc`/`libstdc++` (GPL z wyjątkiem runtime). Nie dotyczy nas: obraz workera to `python:3.14-slim` na glibc ([ADR-0012](0012-obraz-bazowy-slim.md)).

Kształt wyniku: strona PDF = `Page` z tym samym numerem. Na stronie linie tekstu i tabele posortowane po pozycji pionowej; tekst wewnątrz tabeli trafia tylko do tabeli. W tabeli zostają niepuste komórki w kolejności kolumn (jak w readerach arkuszy, bo ramki dzielą wiersze na wiele cienkich komórek). Znaki ☐ □ ❑ ☒ ☑ w linii tekstu dzielą ją na `Checkbox`-y, tą samą regułą co w DOCX.

Strona z obrazami i bez żadnego znaku = skan: reader rzuca `ScannedPdf` z komunikatem „wymaga OCR”. Limit 100 stron chroni przed „bombą stron”; rozmiar pliku ogranicza walidacja przy wgrywaniu.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| PyMuPDF | AGPL-3.0, zakazany ([ADR-0013](0013-polityka-licencji.md)) |
| pypdf (BSD, bez zależności) | tekst bez pozycji znaków i bez tabel; tabele i kolejność trzeba by pisać od zera |
| pypdfium2 bezpośrednio | szybki tekst, ale bez wykrywania tabel; i tak jest zależnością pdfplumbera |
| pdfminer.six bezpośrednio | to samo co pdfplumber, tylko bez tabel i z niższym API |
| camelot / tabula | tabula wymaga Javy, camelot ciągnie OpenCV i Ghostscript |
| docling, unstructured | ciężkie, pobierają modele ML, a tekstowe PDF-y ich nie potrzebują |

## Konsekwencje

- Jedna nowa zależność runtime z siedmioma przechodnimi, w tym binarny PDFium (koła dla glibc są na PyPI).
- `cryptography` w środowisku zmienia typy `PyJWT` (klucze RSA/EC zamiast `Any`); test JWT z `alg=none` podaje pusty klucz zamiast `None`.
- Pola wyboru narysowane jako wektorowe kwadraty albo glify z prywatnego obszaru Unicode (np. Wingdings `` w formularzu 3) zostają zwykłym tekstem; Understand widzi je jako znak na początku linii.
- pdfminer dekompresuje strumienie treści w pamięci, więc bomba kompresji w jednym strumieniu nie jest ograniczona limitem stron. Chroni nas limit rozmiaru uploadu i limit pamięci kontenera.
