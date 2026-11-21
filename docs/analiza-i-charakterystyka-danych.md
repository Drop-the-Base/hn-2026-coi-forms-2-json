# Analiza i charakterystyka danych

Stan na 2026-11-21. Źródła: `data/`, `docs/COI - Pełna treść zadania konkursowego.pdf`, `data/Materiały do zadania dla Uczestników/`.

## TL;DR

1. **To nie jest OCR „pole po polu".** Wzorcowe JSON-y to papierowy formularz *przeprojektowany* według dokumentu „Standardy i dobre praktyki". 85–93% elementów każdego wzorca (wzorzec 5: 63 z 73, wzorzec 1: 64 z 69) to te same gotowe sekcje (urząd, podmiot wniosku, Twoje dane, adres, pełnomocnictwo, opłata skarbowa, kontakt, zgoda, strona końcowa).
2. **Unikalna część to tylko „przedmiot wniosku"** (zwykle strona 2): 4 pola we wzorcu nr 1, 7 pól we wzorcu nr 5. To jest właściwa robota dla AI.
3. **Większość JSON-a da się wygenerować deterministycznie**: layout (`x/y/rows/cols`), UUID-y, `flow`, zapytania JSONata i dane inicjalne mają stały, powtarzalny wzór.
4. **Wzorce są niespójne z dokumentacją** (walidacje zawsze puste, inne nazwy słowników, nieudokumentowane klucze). Przed generowaniem trzeba ustalić, co jest źródłem prawdy (lista pytań do mentorów na końcu).
5. **Ograniczenie techniczne**: brak zewnętrznych API LLM, więc model musi działać lokalnie w Dockerze. To wpływa na koszt, czas i jakość ekstrakcji.

## 1. Inwentarz danych

### 1.1 Zestawy formularzy

| # | Formularz | Rola | Strony | Złożoność |
|---|---|---|---|---|
| 1 | Ustalenie numeru porządkowego nieruchomości | **wzorzec** (JSON + wizualizacja) | 2 | — |
| 5 | Stwierdzenie nadpłaty podatku | **wzorzec** (JSON + wizualizacja) | 1 | — |
| 3 | Wydanie zaświadczenia (Młynary) | do oceny | 1 | niska |
| 4 | Wynajem/użyczenie świetlicy (Płoskinia) | do oceny | 1 | niska |
| 2 | Zwrot opłaty skarbowej (Stawiguda) | do oceny | 2 | średnia |
| 7 | Zezwolenie na psy ras agresywnych (Wrocław) | do oceny | 2 | średnia |
| 6 | Zajęcie pasa drogowego | do oceny | 2 | średnio-wysoka |
| 9 | Stypendium/nagroda/wyróżnienie sportowe (Zgierz, 3 w 1) | do oceny | 16 | wysoka |
| 8 | Deklaracja o opłacie za odpady (Gdynia) | do oceny | 6 | najwyższa |

### 1.2 Formaty plików

Każdy zestaw to **ten sam dokument w 6–8 formatach** (eksporty z jednego źródła):

| Format | Charakterystyka | Uwagi dla parsera |
|---|---|---|
| DOCX / DOC | pełny tekst, najlepsza struktura | w nr 8 kolejność tekstu jest pomieszana (pola tekstowe Worda) |
| PDF | ma warstwę tekstową (nie skan) | dobry do layoutu |
| XLSX / ODS | arkusz „Formularz", układ na scalonych komórkach (np. 759 scaleń w nr 8), nr 9 ma 4 arkusze | tekst jest, ale struktura to siatka komórek |
| JPG / JPEG / PNG | renderowane strony A4, szerokość 1654 px (~200 dpi), **strony sklejone pionowo** (nr 9: 1654×37424 px = 16 stron) | wymaga OCR/VLM i cięcia na strony |

Pułapki formatów (ważne dla walidacji MIME z wymagań):
- `*.DOC` w zestawach 5 i 7 to w rzeczywistości **DOCX** (OOXML). Weryfikacja „zawartość zgodna z rozszerzeniem" odrzuci je, jeśli porównamy ściśle.
- Rozszerzenia wielkimi literami: `.PDF`, `.JPG`, `.PNG`, `.ODS`, a także `.JPE`.
- Zestaw 7 nie ma XLSX ani prawdziwego DOC.

## 2. Struktura docelowego JSON-a (wzorce 1 i 5)

### 2.1 Hierarchia

```
form { title, tabs[], flow.links[] }
└─ tab { id, title, type: MAIN|FINISH, questions[] }
   └─ question { x, y, rows, cols, field }          ← poziom 1: tylko SECTION / REPEATING_SECTION
      └─ field.repeatingSectionGrid[]               ← poziom 2: pola (także w zwykłej SECTION!)
         └─ question { x, y, rows, cols, field }
```

Dzieci zwykłej `SECTION` też leżą w `repeatingSectionGrid`. Schemat ma literówkę `repetingSectionGrid`, a dane używają `repeatingSectionGrid`. Trzymamy się danych.

### 2.2 Statystyki

| | Wzorzec 1 | Wzorzec 5 |
|---|---|---|
| Strony | 3× MAIN + FINISH | 3× MAIN + FINISH |
| Sekcje | 16 | 18 |
| TEXT_FIELD | 36 | 34 |
| SELECT | 6 | 6 |
| FILE_UPLOADER | 4 | 5 |
| RADIO | 3 | 4 |
| TEXT_BLOCK | 3 | 3 |
| NUMBER / TEXTAREA | 0 / 0 | 1 / 1 |
| CONSENT_SECTION | 1 | 1 |
| Stany `SHOW` (JSONata) | 29 | 31 |
| Pola z danymi inicjalnymi | 8 | 9 |

Nieużywane w obu wzorcach: `CHECKBOX`, `DATEPICKER`, `INFO_SECTION`, `REPEATING_SECTION`, stan `READ_ONLY`, rozgałęziony `flow`. Formularze docelowe tych typów **potrzebują** (patrz sekcja 4), a my nie mamy na nie przykładu.

### 2.3 Reguły, które da się wyliczyć kodem (bez AI)

- **Layout**: zawsze `x=0`, `cols=3`; pole ma `rows=1`; sekcja ma `rows` = liczba dzieci; `y` sekcji to suma `rows` poprzednich sekcji; `y` pola to indeks w sekcji. Kolejność w tablicy jest dowolna, liczą się `y`/`questionOrder`.
- **ID**: UUID v4 dla stron i pól. W `flow.links[].id` wzorzec 5 ma krótkie ID (`"a16ec"`), więc format nie jest walidowany.
- **flow**: liniowy łańcuch stron `tab[i] → tab[i+1]`.
- **techName**: snake_case, po polsku bez znaków diakrytycznych, wywiedziony z etykiety. Sufiksy kontekstu: `_zagranica`, `_siedziba`, `_inna_osoba`. Musi być unikalny, bo JSONata odwołuje się po techName.
- **JSONata SHOW**: jeden szablon:
  ```
  "<opcja>" in tabs['<tytuł strony>' in title].questions['<techName sekcji>' in field.techName]
    .field.repeatingSectionGrid['<techName pola>' in field.techName].field.__userAnswer
  ```
  plus `$not(...)`, `and`, `or`. **Odwołanie idzie po tytule strony**, więc zmiana tytułu strony psuje warunki.
- **Dane inicjalne**: `defaultValue: "ŹRÓDŁO.atrybut"` + `defaultValueType: "EXTERNAL_SYSTEM"`. Źródła: `PESEL`, `PESEL_ADDRESS`, `MLPZ`.
- **Opisy**: HTML (`<html><head></head><body>…</body></html>`), także pusty. W zgodzie jest link i obrazek base64.

## 3. Części wspólne: gotowe bloki ze Standardów

Wzorce 1 i 5 mają **prawie identyczną stronę 1 i 3**. Różnią się tylko stroną 2.

| Blok (Standardy) | Kiedy | Zawartość | Zależności |
|---|---|---|---|
| Urząd / Organ, do którego składany jest wniosek | zawsze | TEXT_FIELD readOnly z nazwą urzędu | — |
| Podmiot wniosku | gdy można działać za kogoś | RADIO Swoim / Innej osoby / Osoby prawnej; RADIO Pełnomocnik / Reprezentant | drugie radio widoczne tylko przy „Osoby prawnej" |
| Twoje dane | zawsze | imię, nazwisko, (PESEL), readOnly z rejestru | — |
| Adres zamieszkania / siedziby / innej osoby | per podmiot | Kraj (słownik Kraje, domyślnie Polska), dla PL: TERYT + kod + ulica + nr, dla zagranicy: miejscowość/kod/ulica | przełącznik PL / zagranica |
| Dane innej osoby + adres | „Innej osoby" | imię, nazwisko, (PESEL) | SHOW |
| Dane podmiotu + adres siedziby | „Osoby prawnej" | nazwa, NIP, REGON, KRS | SHOW |
| Pełnomocnictwo | inna osoba LUB (podmiot AND pełnomocnik) | FILE_UPLOADER | SHOW (and/or) |
| Opłata skarbowa v1 | „Innej osoby" | RADIO Tak/Nie, TEXT_BLOCK 17 zł, plik | plik widoczny przy „Tak" |
| Opłata skarbowa v2 | podmiot AND pełnomocnik | TEXT_BLOCK, plik | SHOW |
| Potwierdzenie, że jesteś reprezentantem | podmiot AND reprezentant | FILE_UPLOADER | SHOW |
| Dane do kontaktu | zawsze (przedostatnia strona) | telefon, e-mail z MLPZ | — |
| Zgoda | zawsze | CONSENT_SECTION, link do klauzuli | — |
| Strona końcowa (FINISH) | zawsze | podgląd, TEXT_BLOCK | — |

Wniosek: generator = **biblioteka szablonów bloków** + decyzja „kto może złożyć wniosek" + AI dla strony z przedmiotem wniosku.

## 4. Formularze do oceny: co trzeba z nich wyciągnąć

| # | Unikalna treść (strona 2+) | Nowe typy / wyzwania |
|---|---|---|
| 3 Zaświadczenie | lista rodzajów zaświadczeń + „inne", cel | CHECKBOX, pole „inne" widoczne warunkowo; informacja o opłacie 17 zł jako TEXT_BLOCK |
| 4 Świetlica | wynajem/użyczenie, termin od–do, cel, liczba uczestników, osoba odpowiedzialna | RADIO, DATEPICKER, NUMBER; „inna osoba odpowiedzialna" wymaga zgody (plik); oświadczenia jako CONSENT_SECTION |
| 2 Zwrot opłaty skarbowej | data i kwota opłaty, organ, uzasadnienie, sposób zwrotu (gotówka/przelew) | DATEPICKER, NUMBER, TEXTAREA; nr rachunku i dane właściciela widoczne tylko przy przelewie; pełnomocnik jest na papierze, więc mapujemy go na blok Pełnomocnictwo |
| 7 Psy | dane psa: pochodzenie, rasa, data urodzenia, płeć, oznakowanie, miejsce utrzymania | **REPEATING_SECTION** („więcej niż jeden pies"); **tytuł mówi o psach agresywnych, a treść o chartach** (prawo łowieckie) |
| 6 Pas drogowy | droga, działka, rodzaj robót, powierzchnie (4 kategorie × długość × szerokość = m²), termin, wykonawca | tabela jako REPEATING_SECTION lub NUMBER-y; obliczenia m² (brak mechanizmu w JSON-ie); 6 załączników, część warunkowych |
| 9 Stypendium 3w1 | rodzaj wniosku, wnioskodawca (Prezydent / Klub), reprezentant / pełnomocnik klubu, sportowiec, dyscypliny (20+), osiągnięcia, zgody pełnoletni / nieletni | wybór typu steruje treścią (SHOW albo strony alternatywne); walidatory **EPUAP, ADE, SERIAL_NUMBER_ID_CARD**; SELECT z wyszukiwarką; kandydat na nowy słownik |
| 8 Deklaracja odpady | 69 numerowanych pozycji, części A–G, załączniki A/B, współmałżonek, adres korespondencyjny, okoliczności z datą, wyliczenie opłaty (liczba gospodarstw × stawka, sumy) | najwięcej warunków; pola wyliczane (brak typu „formula"); najsłabsza ekstrakcja z DOC |

Elementy papieru, które **usuwamy lub zamieniamy** (wynika ze Standardów i wzorca 5 vs jego PDF):

| Na papierze | W eUsłudze |
|---|---|
| podpis, „miejscowość, dnia", pieczęć, „wypełnia organ", „WIELKIMI LITERAMI" | usunąć |
| pełna klauzula RODO, podstawa prawna | usunąć, w zgodzie zostaje tylko link |
| nazwisko/adres wnioskodawcy | Twoje dane z rejestru + blok adresu |
| „Nazwisko i imię / Nazwa firmy", PESEL* / NIP* | Podmiot wniosku + Dane podmiotu |
| „* niepotrzebne skreślić" | RADIO |
| „Jeśli wybierzesz tę formę, wpisz…" | stan SHOW |
| „W załączeniu: 1) … 2) …" | FILE_UPLOADER-y |
| adresat (urząd/wójt) | sekcja Urząd/Organ, readOnly z wartością domyślną |

## 5. Niespójności: wzorce vs dokumentacja

| # | Problem | Gdzie | Wpływ |
|---|---|---|---|
| 1 | `validation` **zawsze puste**, a czasem `{}` zamiast `[]`. Standardy wymagają REQUIRED, PESEL, NIP, EMAIL, ZIP_CODE. Reguły: „każde pole musi mieć atrybut obligatoryjności" | oba wzorce | nie znamy formatu wpisu walidacji (zakładamy `["REQUIRED","PESEL"]`) |
| 2 | Nazwy słowników: wzorce używają `Kraje`, `TERYT_4G_DOWODOWY`, `TERYT_DOWODOWY`. Dokument „Słowniki" wymienia Województwo / Powiat / Gmina / Miejscowość / Kraje / Numery kierunkowe | wzorce vs Słowniki.docx | które nazwy wpisywać w `dictionaryName`? |
| 3 | TERYT to jedna lista kaskadowa (`multiLevelTree: true`) zamiast 4 list; `title` pola = nazwa słownika | wzorce | klucz `multiLevelTree` nieopisany |
| 4 | Klucze spoza schematu: `multiLevelTree`, `searchEnabled` (opisany w regułach, brak w schemacie), `defaultValue` jako tablica (`["Polska"]`, `[]`), choć schemat mówi string | wzorce vs schemat | walidacja schematem odrzuci poprawny wzorzec |
| 5 | Pola adresu z `EXTERNAL_SYSTEM` mają `readOnly: false`. „Dane inicjalne": pole z rejestru *musi* być readOnly | wzorce | sprzeczne reguły |
| 6 | Twoje dane: wzorzec 1 bierze `MLPZ.name`, wzorzec 5 `PESEL.name`. Standardy mówią MLPZ | wzorce | które źródło? |
| 7 | FINISH: reguły mówią „wyłącznie INFO_SECTION", a wzorce mają SECTION + TEXT_BLOCK | reguły vs wzorce | co przejdzie import? |
| 8 | Wzorce pomijają pola ze Standardów: PESEL w Dane innej osoby, REGON/KRS w Dane podmiotu (nr 5), checkbox „Brak kodu pocztowego" | wzorce | brak klucza JSON na checkbox „Brak …" |
| 9 | Standardy każą podać limity plików (rozmiar, formaty, liczba), ale w JSON-ie nie ma na nie klucza | Standardy vs schemat | pominąć albo dać do `description` |
| 10 | Standardy: Ulica ma walidację „Kod pocztowy" | Standardy | błąd kopiuj-wklej, ignorujemy |

## 6. Na czym polega problem (w kontekście wymagań)

### 6.1 Zadanie w jednym zdaniu

REST API przyjmuje 1 plik (PDF/DOC/DOCX/ODS/XLSX/JPG/PNG) i zwraca JSON konfiguracji eUsługi, który (a) oddaje treść formularza, (b) ma strukturę wzorców, (c) spełnia Standardy projektowania.

### 6.2 Podział na podproblemy

| Etap | Trudność | Podejście |
|---|---|---|
| 1. Ingest: plik → tekst + układ | średnia | DOCX/PDF/XLSX/ODS: parsery bez AI. Obrazy: OCR lub lokalny VLM, cięcie na strony A4 |
| 2. Rozumienie: kto składa, jakie pola i typy, warunki, załączniki, opłaty | **wysoka**, tu jest AI | lokalny LLM z wyjściem strukturalnym (JSON pośredni, nie finalny) |
| 3. Mapowanie na bloki Standardów | średnia | reguły: osoba fizyczna / firma / pełnomocnik → zestaw bloków |
| 4. Budowa JSON-a | niska | kod: szablony, layout, UUID, flow, JSONata, dane inicjalne |
| 5. Walidacja wyniku | niska | schemat + reguły techniczne (≥2 strony, ostatnia FINISH, brak inputów na FINISH, brak zagnieżdżonych sekcji, unikalne techName, tytuł ≤255 znaków, spójny flow) |

### 6.3 Wymagania obowiązkowe poza samym AI

- Walidacja MIME vs rozszerzenie (pułapka: `.DOC` = DOCX), nazwa pliku ≤250 znaków bez `; : > < / \ | ' * % $`, konfigurowalny limit rozmiaru.
- Pliki tylko w pamięci lub w katalogu tymczasowym na czas żądania.
- Docker: oficjalny obraz, przypięta wersja (bez `latest`), użytkownik bez uprawnień roota, sekrety w runtime, konfiguracja **JWT**.
- README: build, uruchomienie, konfiguracja, opis API.
- Java 21+ lub Python 3.14+, tylko licencje bez copyleftu, **brak LLM przez API** w działającym rozwiązaniu.
- Obrona: uruchomienie na **nowych, nieznanych plikach**, więc nie wolno hardkodować 7 formularzy.

### 6.4 Rozszerzenia punktowane i ich pokrycie przez dane

| Rozszerzenie | Co mamy w danych |
|---|---|
| I. Słowniki + dane inicjalne | wzorce pokazują format, lista atrybutów PESEL/PESEL_ADDRESS/MLPZ w PDF |
| II. Nowy słownik | kandydaci: **Dyscypliny sportowe** (nr 9), **Rodzaje podatków** (nr 5, dziś TEXT_FIELD), **Rasy psów** (nr 7), **Rodzaj / tytuł władania nieruchomością** (nr 8) |
| III. Zależności | wzorce mają wzór SHOW; brak przykładu READ_ONLY i stron alternatywnych |
| IV. Frontend importu | brak danych, do zaprojektowania |
| V. Wizualizacja JSON | wizualizacje DOCX ze screenami jako referencja wyglądu |
| VI. Walidacje | lista 9 walidatorów, ale brak przykładu formatu (patrz problem nr 1) |

## 7. Pytania do mentorów COI (blokujące)

1. Jaki jest format wpisu w `validation`? Stringi `["REQUIRED","PESEL"]`? Wzorce mają `[]` albo `{}`.
2. `dictionaryName`: używać `TERYT_4G_DOWODOWY` / `Kraje` ze wzorców czy nazw z dokumentu Słowniki?
3. Czy strona FINISH może mieć SECTION + TEXT_BLOCK (jak we wzorcach), czy tylko INFO_SECTION (jak w regułach)?
4. Czy pola z `EXTERNAL_SYSTEM` mają być `readOnly: true` zawsze, także adres?
5. Formularz 7: idziemy za tytułem (psy agresywne) czy za treścią (charty)?
6. Formularz 9: jeden JSON z wyborem rodzaju wniosku, czy strony alternatywne w `flow`?
7. Jak będzie oceniany wynikowy JSON: porównanie z ukrytym wzorcem (wtedy liczą się nazwy techName i kolejność) czy ocena ekspercka?
