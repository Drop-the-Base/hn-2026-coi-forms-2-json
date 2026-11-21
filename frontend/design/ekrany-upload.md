# Makiety: logowanie, upload, lista zadań, postęp

Ścieżka urzędnika „wgraj plik → poczekaj na wynik” ([FR-E4](../../docs/requirements.md), [FR-E6](../../docs/requirements.md), [FR-T3](../../docs/requirements.md), [FR-T5](../../docs/requirements.md)). Ekran przeglądu wyniku jest osobno, w `ekran-przegladu.md` (#48).

Wszystkie kolory, odstępy i komponenty pochodzą z [DESIGN.md](../DESIGN.md). W makietach nazwy w nawiasach kwadratowych to komponenty z DESIGN.md §5, np. `[primary]` = przycisk primary, `[badge]` = badge confidence. Teksty w makietach to docelowe teksty interfejsu.

Legenda ASCII: `[ Etykieta ]` przycisk, `|____|` pole, `( ✓ )` ikona stanu, `▓▓▓░░░` pasek postępu.

## 0. Układ wspólny

```
┌──────────────────────────────────────────────────────────────────────┐
│ Konwerter formularzy                         Zadania   [ Wyloguj ]   │  nagłówek: tło bg, dolna linia border
├──────────────────────────────────────────────────────────────────────┤
│ [Przejdź do treści]  ← link widoczny tylko przy fokusie               │
│                                                                      │
│  <tytuł strony, --text-2xl>                                          │
│  <treść ekranu, max ~72rem, padding --space-8>                        │
└──────────────────────────────────────────────────────────────────────┘
```

- Po zmianie ekranu fokus trafia na `h1` (`tabindex="-1"`), a tytuł karty przeglądarki zmienia się na „<Ekran> – Konwerter formularzy”.
- Po zalogowaniu ekranem startowym jest „Zadania” (upload + lista na jednej stronie), bo urzędnik wraca tu po każdym pliku.

## 1. Logowanie (token JWT)

API tylko weryfikuje JWT ([FR-10](../../docs/requirements.md)), nie wydaje go. Dlatego logowanie to wklejenie tokena, który urzędnik dostaje od administratora. Gdy backend dostanie endpoint logowania loginem i hasłem, ten ekran zmieni się w zwykły formularz logowania (osobny PR).

```
┌────────────────────────────────────────────┐
│  Zaloguj się                                │  [karta], wyśrodkowana, szer. ~28rem
│                                            │
│  Token dostępu (wymagane)                  │  [pole], type="password"
│  Token JWT otrzymany od administratora.    │  opis, text-muted
│  |______________________________________|  │
│  [ ] Pokaż token                            │  checkbox przełącza type
│                                            │
│  [ Zaloguj ]                                │  [primary], pełna szerokość
└────────────────────────────────────────────┘
```

Zachowanie:
- „Zaloguj” sprawdza token zapytaniem do API (np. `GET /api/v1/jobs`). Przycisk w stanie ładowania: „Logowanie…”.
- Token trzymamy tylko w pamięci aplikacji. Odświeżenie strony = ponowne logowanie. Nie dajemy go do `localStorage` ani do adresu URL.
- `401` w dowolnym momencie pracy wraca na ten ekran z komunikatem „Sesja wygasła. Zaloguj się ponownie.” ([karta stanu] `info`), a rozpoczęte uploady zostają przerwane.

Błędy (stan error pola z DESIGN.md, komunikat pod polem):

| Sytuacja | Komunikat |
|---|---|
| puste pole | „Wklej token dostępu.” |
| API zwraca 401 | „Token jest nieprawidłowy albo wygasł. Poproś administratora o nowy.” |
| brak połączenia | [karta stanu] `error` nad formularzem: „Nie można połączyć się z serwerem. Spróbuj ponownie za chwilę.” |

## 2. Zadania: upload i lista

Jeden ekran: strefa wgrywania u góry, lista zadań pod nią.

### 2.1. Strefa wgrywania (pusta)

```
Zadania                                                        h1
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │  strefa: ramka 2px przerywana border-strong,
│               Przeciągnij pliki tutaj albo                           │  tło surface, --radius-lg
│                     [ Wybierz pliki ]                                │  [primary]
│                                                                      │
│   PDF, DOC, DOCX, ODS, XLSX, JPG, JPEG, PNG · do 20 MB na plik       │  text-muted, --text-sm
│   Możesz wgrać kilka plików naraz.                                   │
└──────────────────────────────────────────────────────────────────────┘
```

- Przycisk to `<input type="file" multiple accept=".pdf,.doc,.docx,.ods,.xlsx,.jpg,.jpeg,.png">` ukryty za `[primary]`. Strefa drag&drop jest tylko skrótem dla myszy; przycisk wystarcza do pełnej obsługi z klawiatury.
- Limit rozmiaru w opisie pochodzi z konfiguracji API ([FR-05](../../docs/requirements.md)); „20 MB” to przykład.
- Przeciąganie nad strefą: ramka ciągła 2px `primary`, tło `primary-subtle`, tekst „Upuść, aby dodać pliki”.

### 2.2. Pliki wybrane: walidacja przed wysłaniem

Po wybraniu lub upuszczeniu plików pod strefą pojawia się lista do wysłania. Jeden plik i wiele plików to ten sam widok (batch, [FR-E6](../../docs/requirements.md)).

```
Do wysłania (4)                                                     h2
┌──────────────────────────────────────────────────────────────────────┐
│ ( ✓ ) wniosek_o_dowod.pdf                       2,1 MB   [ Usuń ]    │  [ghost] Usuń
│ ( ✓ ) KARTA_ZGLOSZENIA.DOC                      0,4 MB   [ Usuń ]    │
│ ( ✕ ) skan;strona1.jpg                          1,2 MB   [ Usuń ]    │
│       Nazwa zawiera niedozwolony znak „;”. Zmień nazwę pliku.        │  tekst error, ikona ✕
│ ( ✕ ) archiwum.zip                              3,0 MB   [ Usuń ]    │
│       Ten format nie jest obsługiwany. Dozwolone: PDF, DOC, DOCX,    │
│       ODS, XLSX, JPG, JPEG, PNG.                                     │
└──────────────────────────────────────────────────────────────────────┘
2 pliki nie przejdą walidacji i nie zostaną wysłane.                     tekst warning z ikoną !
                                    [ Wyczyść listę ]  [ Wgraj 2 pliki ]  [secondary] [primary]
```

- Walidacja w przeglądarce (szybka informacja, nie zabezpieczenie): rozszerzenie bez rozróżniania wielkości liter, długość i znaki nazwy, rozmiar. Serwer i tak sprawdza wszystko jeszcze raz, w tym MIME z zawartości ([FR-02..FR-05](../../docs/requirements.md)).
- Pliki z błędem zostają na liście z komunikatem, żeby urzędnik wiedział, czego brakuje. Nie są wysyłane.
- Etykieta przycisku mówi, ile plików pójdzie: „Wgraj plik”, „Wgraj 2 pliki”, „Wgraj 5 plików”. Gdy żaden plik nie jest poprawny, przycisk jest wyłączony (`disabled`).
- Po kliknięciu: przycisk „Wgrywanie…” (`aria-busy`), każdy plik idzie osobnym `POST /api/v1/jobs`. Po `202` plik znika z listy „Do wysłania” i pojawia się w liście zadań jako „W kolejce”.

Komunikaty walidacji (pod nazwą pliku):

| Reguła | Gdzie | Komunikat |
|---|---|---|
| format (FR-02) | przeglądarka + serwer | „Ten format nie jest obsługiwany. Dozwolone: PDF, DOC, DOCX, ODS, XLSX, JPG, JPEG, PNG.” |
| MIME z zawartości (FR-03) | tylko serwer | „Zawartość pliku nie pasuje do rozszerzenia .pdf. Sprawdź, czy plik nie jest uszkodzony albo nie ma złego rozszerzenia.” |
| nazwa > 250 znaków (FR-04) | przeglądarka + serwer | „Nazwa pliku ma 263 znaki, a może mieć najwyżej 250. Skróć nazwę.” |
| zakazane znaki (FR-04) | przeglądarka + serwer | „Nazwa zawiera niedozwolony znak „;”. Usuń znaki: ; : > < / \ \| ' * % $” |
| rozmiar (FR-05) | przeglądarka + serwer | „Plik ma 34,5 MB, a limit to 20 MB.” |
| pusty plik | przeglądarka | „Plik jest pusty.” |
| odrzucenie przez serwer (inne 4xx/5xx) | serwer | „Nie udało się wysłać pliku. Spróbuj ponownie.” + `[ghost] Spróbuj ponownie` |

Błąd z serwera (np. MIME) pokazuje się w tym samym miejscu co błąd z przeglądarki: plik wraca na listę „Do wysłania” z komunikatem.

### 2.3. Lista zadań

```
Twoje zadania                                       [ Odśwież ]     h2, [ghost]
┌────────────────────────────┬─────────────────────┬──────────┬────────────────┬──────────────┐
│ Plik                       │ Status              │ Czas     │ Pewność ogólna │              │  nagłówek tabeli
├────────────────────────────┼─────────────────────┼──────────┼────────────────┼──────────────┤
│ wniosek_o_dowod.pdf        │ ( ✓ ) Gotowe        │ 0:42     │ ✓ Wysoka 0,91  │ [ Przejrzyj ] │
│ KARTA_ZGLOSZENIA.DOC       │ ( ! ) 3 ostrzeżenia │ 1:05     │ ! Średnia 0,72 │ [ Przejrzyj ] │
│ skan_wniosku.jpg           │ ( ◔ ) W toku: 1/4   │ 0:18     │ —              │ [ Postęp ]    │
│ zalacznik.xlsx             │ ( … ) W kolejce     │ —        │ —              │               │
│ formularz_stary.pdf        │ ( ✕ ) Błąd          │ 0:07     │ —              │ [ Szczegóły ] │
└────────────────────────────┴─────────────────────┴──────────┴────────────────┴──────────────┘
```

- Kolumny: Plik, Status, Czas (od wysłania do końca; dla zadań w toku liczy się na żywo, format m:ss), Pewność ogólna ([badge] confidence z FR-T1), akcja w wierszu (`[ghost]`).
- Kolejność: najnowsze na górze. Sortowanie po kolumnach przez przyciski w nagłówku (`aria-sort`), zgodnie z tabelą z DESIGN.md.
- Wiersz w toku aktualizuje się ze zdarzeń SSE (§3); gdy SSE nie działa, lista co 5 s pyta `GET /api/v1/jobs/{id}` (zapas z ADR-0014).
- „Przejrzyj” prowadzi do ekranu przeglądu (#48), „Postęp” do §3, „Szczegóły” do §4.2.
- Wyniki trzyma API w pamięci z TTL (NFR-06), więc lista pokazuje tylko zadania z bieżącej sesji. Po wygaśnięciu: status „Wygasło”, opis w §4.

Statusy (zawsze ikona + tekst, nigdy sam kolor):

| Status | Ikona | Kolor tekstu | Kiedy |
|---|---|---|---|
| W kolejce | … | `text-muted` | po `202`, przed pierwszym zdarzeniem |
| W toku: n/4 | ◔ (spinner, statyczny przy `prefers-reduced-motion`) | `info` | trwa krok n z 4 |
| Gotowe | ✓ | `success` | wynik bez ostrzeżeń |
| n ostrzeżenia / ostrzeżeń | ! | `warning` | gotowe, ale wynik ma ostrzeżenia (issues) |
| Błąd | ✕ | `error` | przetwarzanie przerwane |
| Wygasło | ⧗ | `text-muted` | wynik usunięty po TTL |

## 3. Postęp na żywo (SSE)

Otwiera się po „Postęp” w liście albo automatycznie, gdy urzędnik wgrał dokładnie jeden plik. Źródło: `GET /api/v1/jobs/{id}/events`, zdarzenia `{step, status, message, progress}` (ADR-0014).

```
← Wróć do zadań                                                     link
Przetwarzanie: skan_wniosku.jpg                                     h1
Czas: 0:48                                                          text-muted, tabular-nums

┌──────────────────────────────────────────────────────────────────────┐
│ Krok 1 z 4: Odczyt pliku                                             │  --text-lg
│ OCR strony 3/16                                                      │  message ze zdarzenia
│ ▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░  19%                                  │  <progress>, gdy jest progress
└──────────────────────────────────────────────────────────────────────┘

  ( ✓ ) 1. Odczyt pliku            gotowe, 0:31                     <ol>, kroki
  ( ◔ ) 2. Analiza treści          w toku…                          aria-current="step"
  (   ) 3. Budowa formularza       czeka
  (   ) 4. Sprawdzenie reguł       czeka

Ostrzeżenia (2)                                                     h2
┌──────────────────────────────────────────────────────────────────────┐
│ ( ! ) Strona 5: słaba jakość skanu, tekst może zawierać błędy.       │  [karta stanu] warning
│ ( ! ) Nie rozpoznano adresata wniosku.                               │
└──────────────────────────────────────────────────────────────────────┘

                                               [ Przejrzyj wynik ]   [primary], aktywny po zakończeniu
```

Nazwy kroków dla urzędnika (bez żargonu; nazwy techniczne z architecture.md §4 tylko w kodzie):

| Krok w pipeline | Tekst w UI | Przykładowe komunikaty |
|---|---|---|
| 1. Ingest | Odczyt pliku | „Konwersja DOC do DOCX”, „OCR strony 3/16” |
| 2. Understand | Analiza treści | „Analiza przez model językowy” |
| 3. Compose | Budowa formularza | „Składanie stron formularza” |
| 4. Validate | Sprawdzenie reguł | „Walidacja: 2 ostrzeżenia” |

Zachowanie:
- Pasek postępu pokazujemy tylko, gdy zdarzenie ma `progress`; bez niego sam tekst kroku i spinner (nie udajemy postępu).
- Ostrzeżenia dopisują się na dole listy w kolejności przyjścia, nie przesuwają reszty ekranu w górę.
- Po `done` kroku 4: karta zmienia się na [karta stanu] `success` „Gotowe. Pewność ogólna: [badge] Średnia 0,72”, przycisk „Przejrzyj wynik” staje się aktywny. Fokus zostaje tam, gdzie był (nie skaczemy).
- Zerwane połączenie SSE: pod kartą tekst `text-muted` „Połączenie przerwane, sprawdzamy stan co kilka sekund…”, przejście na polling. Po powrocie SSE tekst znika.
- Wyjście z ekranu nie przerywa zadania; postęp widać dalej w liście.

## 4. Stany puste i błędy

### 4.1. Brak zadań

```
Twoje zadania                                                       h2
┌──────────────────────────────────────────────────────────────────────┐
│ Brak zadań. Wgraj pierwszy formularz.                                │  pusta tabela z DESIGN.md, text-muted
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2. Błąd przetwarzania (szczegóły zadania)

```
← Wróć do zadań
Przetwarzanie: formularz_stary.pdf                                  h1
┌──────────────────────────────────────────────────────────────────────┐
│ ( ✕ ) Nie udało się przetworzyć pliku                                │  [karta stanu] error
│ Krok 1 z 4: Odczyt pliku. Plik PDF jest zaszyfrowany hasłem.         │  message ze zdarzenia failed
│ Zdejmij hasło z pliku i wgraj go ponownie.                           │
└──────────────────────────────────────────────────────────────────────┘
  ( ✕ ) 1. Odczyt pliku     błąd
  (   ) 2. Analiza treści   pominięto
  (   ) 3. Budowa formularza pominięto
  (   ) 4. Sprawdzenie reguł pominięto
                                                      [ Wgraj inny plik ]   [primary], wraca do §2 i ustawia fokus na „Wybierz pliki”
```

Plik nie jest już dostępny (usuwany po zakończeniu, NFR-06), więc nie ma „Spróbuj ponownie” dla tego zadania; urzędnik wgrywa plik od nowa.

### 4.3. Pozostałe

| Stan | Gdzie | Treść |
|---|---|---|
| brak połączenia z API | [karta stanu] `error` nad listą | „Nie można połączyć się z serwerem. Lista może być nieaktualna.” + `[secondary] Spróbuj ponownie` |
| wynik wygasł (TTL) | wiersz listy / ekran postępu | „Wynik wygasł i został usunięty. Wgraj plik ponownie.” |
| nieznane zadanie (404) | ekran postępu | „Nie ma takiego zadania. Mogło wygasnąć.” + link „Wróć do zadań” |
| sesja wygasła (401) | ekran logowania | jak w §1 |

## 5. Dostępność (NFR-15, WCAG 2.1 AA)

Kolejność fokusu (Tab):
1. Logowanie: pole „Token dostępu” → „Pokaż token” → „Zaloguj”. Przy błędzie fokus wraca na pole, komunikat podpięty przez `aria-describedby`.
2. Zadania: „Przejdź do treści” → nagłówek (Zadania, Wyloguj) → „Wybierz pliki” → lista „Do wysłania” (po kolei „Usuń” w każdym wierszu) → „Wyczyść listę” → „Wgraj n plików” → „Odśwież” → nagłówki sortowania → akcje w wierszach tabeli.
3. Postęp: „Wróć do zadań” → „Przejrzyj wynik” (wyłączony do końca przetwarzania, ale osiągalny przez `aria-disabled="true"` zamiast `disabled`, żeby czytnik go ogłosił).
4. Po „Usuń” fokus przechodzi na następny plik na liście, a gdy go nie ma, na „Wybierz pliki”.

Ogłoszenia dla czytnika ekranu:
- Region postępu na ekranie §3: jeden `aria-live="polite"` z tekstem „Krok 2 z 4: Analiza treści”. Ogłaszamy tylko zmianę kroku, nie każdą stronę OCR (inaczej czytnik mówi bez przerwy); `<progress>` ma `aria-label="Postęp kroku"` i można go sprawdzić ręcznie.
- Ostrzeżenia: lista w regionie `aria-live="polite"`, nowe pozycje ogłaszane po kolei.
- Koniec zadania: „Przetwarzanie zakończone. Pewność ogólna: średnia, 0,72.” (`polite`); błąd przetwarzania: `role="alert"`.
- Lista zadań: zmiana statusu ogłaszana jednym zbiorczym `aria-live="polite"` („wniosek_o_dowod.pdf: gotowe”), komórki tabeli nie są regionami live.
- Walidacja plików: po dodaniu plików podsumowanie w `aria-live="polite"`: „Dodano 4 pliki, 2 z błędami.”
- Strefa drag&drop nie jest jedyną drogą: wszystko robi przycisk „Wybierz pliki”.
- Animacje (spinner, pasek) zatrzymane przy `prefers-reduced-motion: reduce`.

## Poza zakresem

Ekran przeglądu i edycji wyniku (#48), anulowanie zadania w toku (API go nie ma), historia zadań między sesjami (wyniki żyją tylko przez TTL), wydawanie tokenów.
