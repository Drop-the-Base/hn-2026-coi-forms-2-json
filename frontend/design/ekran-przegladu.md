# Ekran przeglądu wyniku: [przeglad.html](przeglad.html)

Główny ekran pracy urzędnika (issue #48): widzi, co sprawdzić, poprawia pole w inspektorze albo wprost w JSON-ie, ogląda formularz tak, jak zobaczy go wnioskodawca, i pobiera poprawioną wersję. Wymagania: [FR-T1](../../docs/requirements.md) (confidence, ocena ogólna, lista problemów), [FR-T2](../../docs/requirements.md) (edycja i pobieranie), [FR-E5](../../docs/requirements.md) (podgląd formularza), [FR-06](../../docs/requirements.md) (schemat), [NFR-06](../../docs/requirements.md), [NFR-15](../../docs/requirements.md). Wygląd: [DESIGN.md](../DESIGN.md).

| Stan | Zrzut |
|---|---|
| problemy, bieżący 3 z 7 | [przeglad.png](zrzuty/przeglad.png) |
| JSON niezgodny ze schematem | [przeglad-blad-schematu.png](zrzuty/przeglad-blad-schematu.png) |
| brak problemów | [przeglad-bez-problemow.png](zrzuty/przeglad-bez-problemow.png) |
| wyjście z niepobranymi poprawkami | [przeglad-wyjscie.png](zrzuty/przeglad-wyjscie.png) |
| wąski ekran (zakładki) | [przeglad-390.png](zrzuty/przeglad-390.png) |

Dane z backendu (kontrakt z #97 / PR #100, opisany w komentarzu do #54; źródło prawdy to backend):

```
{form, confidence: {overall, elements: {<ścieżka JSON>: 0..1}, to_review: [<ścieżka>]},
 issues: [{code, message, path, severity: "ERROR"|"WARNING"}],
 usage: {prompt_tokens, completion_tokens, seconds}}
```

- Elementy wskazuje **ścieżka JSON**, np. `tabs[1].questions[0].field.repeatingSectionGrid[2].field` (to samo w `confidence.elements`, `to_review` i `issues[].path`). Edytor znajduje element po ścieżce w tekście, podgląd po ścieżce pola na stronie; ścieżka do właściwości pola (`…field.options`) wskazuje to pole.
- `severity`: `ERROR` = „Błąd”, `WARNING` = „Do sprawdzenia”. Elementy z `to_review` (poniżej progu) dochodzą do listy jako „Do sprawdzenia” z badge pewności.
- Confidence **nie trafia** do pobieranego JSON-a: pobieramy samo `form` po poprawkach, bo plik musi przejść schemat eUsługi.
- Nieudane zadanie: `error` to sam typ błędu (np. `UnsupportedFormat`); polski komunikat dobiera frontend (`features/jobs/jobError.ts`), nieznany typ dostaje komunikat ogólny z kodem.
- Próg podświetlenia `REVIEW_THRESHOLD` = 0,85 (poziom średni i niski z DESIGN.md), niska pewność poniżej 0,60.
- JSON Schema eUsługi nie jest wbudowany we frontend: backend podaje ją przez `GET /api/v1/form-schema` (plik `backend/src/forms2json/domain/schema.json`). Strona zadania pobiera ją raz na sesję, zanim pokaże ekran: w trakcie „Wczytywanie ekranu przeglądu…”, przy błędzie alert „Nie udało się pobrać schematu eUsługi, więc nie da się sprawdzić wyniku.” z przyciskiem „Spróbuj ponownie”.

## 1. Układ (> 64rem)

Ekran nie przewija się jako całość: stałe nagłówki, a pod nimi lista i dwie kolumny robocze, każda z własnym przewijaniem. W każdej kolumnie roboczej urzędnik sam wybiera widok: Pole, JSON, Oryginał albo Podgląd. Dzięki temu dowolna para stoi obok siebie, np. oryginał i pole, oryginał i JSON, oryginał i podgląd, pole i podgląd.

```
┌ pasek aplikacji ─────────────────────────────────────────────────────────────────────────────┐
│ Wniosek o ustalenie numeru porządkowego nieruchomości  Ocena ogólna [▨ Średnia 0,78] [Pobierz JSON] │
├ Problem 3 z 7 ⚠ Do sprawdzenia  Niepewny typ pola… (ścieżka)  [█ Niska 0,41]  [‹ Poprzedni] [Następny ›] ┤  przyklejony
├────────────────┬──────────────────────────────────┬──────────────────────────────────────────┤
│ Struktura │Problemy 7│ Pole │ JSON │ Oryginał │ Podgląd│ Pole │ JSON │ Oryginał │ Podgląd     │
│ █ Dane       ⚠ │ Pole tekstowe  [█ Niska 0,41]    │ ┌ skan / PDF / dokument ──────────────┐ │
│   Imię         │ Tytuł [Miejscowość          ]    │ │  Miejscowość: ______________        │ │
│ Informacje o b.│ Rodzaj pola [Pole tekstowe ▾]    │ │  Ulica: ____________________        │ │
│▐█ Miejscowość ⚠│ Reguły ☑ Wymagane ☐ Tylko do…    │ │                                     │ │
│    Ulica       │ Format odpowiedzi ☐ PESEL …      │ └─────────────────────────────────────┘ │
│                ├──────────────────────────────────┴──────────────────────────────────────────┤
│                │ ✓ Zgodny ze schematem eUsługi                                               │
└────────────────┴─────────────────────────────────────────────────────────────────────────────┘
  18rem (17rem       kolumna A: 1fr                     kolumna B: 1fr
  przy ≤ 92rem)      (tu: Pole)                         (tu: Oryginał)        █ = znacznik marginesu
```

- **Lista** (18rem; 17rem przy ≤ 92rem, czyli laptopy 13"): zakładki „Struktura” (drzewo §4) i „Problemy N” (lista §4). Domyślna jest „Problemy”, gdy są problemy, inaczej „Struktura”.
- **Kolumna A i kolumna B**: ta sama czwórka zakładek: „Pole” (inspektor §5), „JSON” (edytor §6, „Formatuj” w nagłówku kolumny), „Oryginał” (wgrany dokument, nazwa pliku w nagłówku) i „Podgląd” (§7). Domyślnie A = Pole, B = Podgląd. Wybór w jednej kolumnie widoku, który jest w drugiej, zamienia kolumny miejscami. Widoki nie montują się od nowa przy przełączaniu (edytor zachowuje historię zmian, podgląd stronę i odpowiedzi).
- **Pasek stanu schematu** (§6) stoi pod obiema kolumnami roboczymi, niezależnie od wybranych widoków; link „Linia N” pokazuje JSON (w kolumnie A, jeśli nie ma go w żadnej).
- F8 i wybór problemu pokazują „Pole” w kolumnie A tylko wtedy, gdy ani pola, ani JSON-a nie ma w żadnej kolumnie; inaczej układ urzędnika zostaje.
- **Niski ekran** (wysokość ≤ 56rem, np. 13" z paskami przeglądarki): nagłówek w jednej linii, bez „← Zadania” (jest w pasku aplikacji), pasek problemu 3rem. Strona dalej się nie przewija, każda kolumna przewija się sama.

## 2. Nagłówek wyniku

| Element | Zachowanie |
|---|---|
| „← Zadania” | powrót do listy; przy niepobranych poprawkach najpierw dialog (§8); ukryty na niskim ekranie |
| tytuł | `title` z bieżącego JSON-a (zmienia się po edycji) |
| metadane | nazwa pliku, początek `job_id` (8 znaków) |
| ocena ogólna | badge z `confidence.overall` |
| licznik | „2 błędy, 5 do sprawdzenia”; przy zerze „Brak problemów” |
| „Pobierz JSON” | jedyny główny przycisk; pobiera aktualną treść edytora jako `<techName-formularza>.json`. Wyłączony tylko, gdy JSON się nie parsuje albo nie przechodzi schematu, z powodem obok („Popraw 1 błąd schematu, aby pobrać.”). Błędy reguł R/S nie blokują: decyduje urzędnik. Bez dialogu przed pobraniem. |

## 3. Pasek „Problem N z M” (przyklejony)

Pokazuje tylko następną decyzję: pozycję, rodzaj (ikona + słowo), opis z `message`, ścieżkę elementu (strona, sekcja, pole), badge pewności, „Poprzedni” / „Następny” (`F8` / `Shift+F8`, `aria-keyshortcuts`). Kolejność: najpierw błędy (reguły, schemat), potem elementy poniżej progu od najniższej pewności. Po ostatnim „Następny” wraca do pierwszego z komunikatem „To był ostatni problem. Wracam do pierwszego.” Przy braku problemów pasek mówi „Brak problemów do sprawdzenia” i zachęca do przejrzenia podglądu.

## 4. Struktura, problemy i wybór elementu

- **Struktura**: drzewo strony → sekcje → pola (kolejność jak na siatce strony), każdy węzeł z tytułem, rodzajem (słowem: „Strona 2”, „Pole tekstowe”), znacznikiem marginesu poniżej progu i ikoną problemu (✕ błąd, ⚠ do sprawdzenia; słowo w nazwie dostępnej). Wybrany węzeł: `aria-current="true"`.
- **Problemy**: `<ol>` przycisków, jeden wiersz = jeden problem: rodzaj, opis, ścieżka, badge (dla `check`). Bieżący wiersz: tło `accent-subtle`, wewnętrzny pasek 3 px `accent`, `aria-current="true"`. Filtr „Pokaż”: Wszystkie / Błędy / Niska pewność.
- Wybór elementu działa tak samo z każdego miejsca: problem (kliknięcie, Enter, pasek, `F8` / `Shift+F8`), węzeł drzewa albo kliknięcie elementu w podglądzie:
  1. inspektor (zakładka „Pole”) otwiera element; tytuł formularza i strony też da się wybrać;
  2. podgląd przełącza stronę na tę z elementem, przewija do niego i zaznacza go (obrys `accent`, tło `accent-subtle`);
  3. przy otwartej zakładce „JSON” edytor przewija do obiektu elementu, podświetla jego linie (`code-current`) i dostaje fokus;
  4. przy problemie `aria-live`: „Problem 3 z 7: Niepewny typ pola Informacje o budynku, Lokalizacja budynku, Miejscowość, pewność niska 0,41.”; brak elementu w JSON-ie dopisuje „Elementu nie ma już w JSON-ie.”
- Element usunięty w edytorze: wiersz z tekstem `muted` „Element usunięty z JSON-a”, przycisk nieaktywny.
- Po edycji: błędy schematu i parsowania liczymy lokalnie od razu. Reguły R/S i confidence liczy backend, więc zmienione elementy dostają dopisek „zmienione, nieprzeliczone”. Ponownej walidacji przez backend nie projektujemy (brak endpointu, YAGNI).

## 5. Inspektor pola („Pole”)

Edycja wybranego elementu kontrolkami zamiast JSON-a (FR-T2). Każda zmiana trafia do tekstu JSON jako jedna zmiana w historii cofania edytora, więc sprawdzanie schematu, podgląd i pobieranie idą za nią.

- Nagłówek: rodzaj pola słowem, badge pewności poniżej progu, ścieżka (strona, sekcja, pole).
- Pola: „Tytuł”; „Rodzaj pola” z zamkniętej listy (Pole tekstowe, Pole tekstowe wielowierszowe, Liczba, Data, Lista rozwijana, Jednokrotny wybór, Pola wyboru, Załącznik, Sekcja, Sekcja powtarzalna, Tekst informacyjny, Zgody; nieznany typ zostaje jako dodatkowa pozycja); „Reguły”: Wymagane (`REQUIRED`), Tylko do odczytu; „Format odpowiedzi”: Adres e-mail, PESEL, NIP, REGON, Kod pocztowy (inne walidatory z JSON-a jako dodatkowe pola wyboru); „Opcje do wyboru” dla SELECT / RADIO / CHECKBOX: lista z „Usuń” i „Dodaj opcję” (`techName` opcji tworzy się z nazwy), nad nią „Słownik”, gdy pole ma `dictionaryName`; „Podpowiedź” (`tooltipMessage`); „Opis” („Opis (HTML)”, gdy zawiera znaczniki); „Warunki” (`states[].query`: „Pokaż, gdy”, „Tylko do odczytu, gdy”); zwinięte „Szczegóły techniczne”: „Nazwa techniczna” i `id`.
- Sekcje, teksty i zgody nie mają reguł, formatu ani podpowiedzi.
- Strona albo formularz: tylko tytuł i wskazówka „Wybierz pole w strukturze albo kliknij je w podglądzie.”
- Błąd składni JSON-a: „JSON ma błąd składni. Popraw go w zakładce JSON, potem wróć tutaj.” Element usunięty: „Tego elementu nie ma już w JSON-ie. Wybierz inny w strukturze.”

## 6. Edytor JSON („JSON”)

- CodeMirror 6 (ADR-0011), `--font-mono` 14 px, numery linii, zwijanie bloków (zwinięty obiekt pokazuje etykietę pola: „Ulica, 14 linii”), kolory składni z tokenów `code-*`.
- Rynna: numer linii, **znacznik marginesu** (pełny / kreskowany przy liniach elementu poniżej progu), kolumna ikon błędu schematu.
- Pasek stanu pod środkową kolumną, przy każdej zakładce (`aria-live="polite"`, podpięty do edytora przez `aria-describedby`):

| Stan | Pasek | „Pobierz JSON” |
|---|---|---|
| poprawny | „Zgodny ze schematem eUsługi” (`success`) | aktywny |
| błąd składni | „Błąd składni w linii 42: brak przecinka.” (`error`) | wyłączony + powód |
| niezgodny ze schematem | „1 niezgodność ze schematem” + lista „Linia 132: „type” ma niedozwoloną wartość „TEXT_FELD”. Czy chodziło o „TEXT_FIELD”?” | wyłączony + powód |

  Linia błędu: ikona ✕ w rynnie i falista linia `error` pod tekstem. „Linia 132” w komunikacie to link, który otwiera zakładkę JSON i stawia tam kursor.
- Walidacja lokalnie względem schematu z `GET /api/v1/form-schema` z poprawką literówki `repeatingSectionGrid` (K-09), ok. 300 ms po ostatnim klawiszu.
- Edytor nie więzi fokusu: `Esc`, potem `Tab` wychodzi (opis w nazwie dostępnej regionu).
- „Formatuj” formatuje cały dokument; jest w historii cofania edytora.

## 7. Podgląd formularza (FR-E5)

- Render tylko do odczytu, w chłodnej palecie `eu-*` odwzorowanej z wizualizacji COI: niebiesko-szare tło, białe karty sekcji, etykieta nad polem, granatowy przycisk „Dalej”. Podpis „tak zobaczy go wnioskodawca w eUsłudze”.
- Kroki stron według `flow.links`, nie kolejności w `tabs[]`; bieżąca `aria-current="step"`; przy stronie z problemami ikona i liczba, w nazwie dostępnej „Strona 2, Informacje o budynku, 3 problemy”. `flow` niespójny: kroki w kolejności `tabs[]` i komunikat `warning` „Przepływ stron jest niespójny. Strony pokazano w kolejności z pliku.”
- Każda karta ma po lewej **margines pewności** (28 px): znacznik przy polu albo sekcji poniżej progu, długi jak element. Obok etykiety badge. Kliknięcie pola albo sekcji wybiera element (§4; wygrywa najgłębszy, więc pole w sekcji wybiera pole). To skrót myszą; z klawiatury wybiera się w strukturze.
- Typy pól: TEXT_FIELD, NUMBER, DATEPICKER → pole; TEXTAREA → pole wieloliniowe; SELECT → lista; RADIO, CHECKBOX → grupy; FILE_UPLOADER → „Dodaj lub przeciągnij plik” (nieaktywny) z limitami jak w eUsłudze; TEXT_BLOCK, INFO_SECTION → tekst; CONSENT_SECTION → checkbox zgody. Nieznany typ: ramka `rule` i „Nieobsługiwany typ pola: X”.
- Kontrolki RADIO i CHECKBOX działają, żeby sprawdzić stany `SHOW` (FR-E3), np. „Innej osoby” odsłania „Dane innej osoby”. Wartości nie trafiają do JSON-a. „Wróć” / „Dalej” przełączają strony podglądu.
- Odświeżenie po każdej zmianie dającej poprawny JSON. Przy błędzie składni lub schematu zostaje ostatni poprawny render z komunikatem `info` „Podgląd sprzed ostatniej zmiany: JSON nie przechodzi schematu.”
- Wydajność: render tylko bieżącej strony formularza.

## 8. Wyjście z niepobranymi poprawkami

Zmiany po ostatnim pobraniu + próba wyjścia („Zadania”, „Wyloguj”, zamknięcie karty przez `beforeunload`): `<dialog>` „Masz niepobrane poprawki. Zmieniłeś JSON po ostatnim pobraniu. Po wyjściu poprawki przepadną, bo serwer ich nie przechowuje.” Akcje: „Zostań” (główna, domyślny fokus) i „Wyjdź bez pobierania” (wariant niszczący, obrys `error`). To jedyny dialog na ekranie.

## 9. Wąski ekran (≤ 64rem)

- Nagłówek się układa w kolumnę, „Pobierz JSON” na pełną szerokość.
- Pasek problemu zostaje przyklejony, opis przechodzi do drugiej linii.
- Zostaje jedna kolumna (A) z zakładkami przyklejonymi pod paskiem problemu: **Pole** (domyślna), **JSON**, **Oryginał**, **Podgląd** i **Lista N** (w środku te same zakładki „Struktura” / „Problemy”). Wybór problemu albo węzła drzewa otwiera zakładkę Pole z wybranym elementem. Strzałki ← → przechodzą między zakładkami. Błąd schematu przy otwartym podglądzie: ikona ✕ na zakładce JSON i komunikat nad podglądem.
- Bez JavaScriptu obszary stoją jeden pod drugim. Strona przewija się jako całość, ale nie poziomo; długie linie edytora przewijają się w jego kontenerze.

## 10. Dostępność (NFR-15)

- Skip link „Przejdź do edycji” (środkowa kolumna). Tabulacja: nagłówek → pasek problemu → lewa kolumna → edycja → podgląd.
- Skróty: `F8` / `Shift+F8` następny / poprzedni problem (`aria-keyshortcuts`); opis w stopce listy.
- Fokus po przejściu do problemu zostaje tam, skąd przyszło polecenie (lista, pasek); na zakładce JSON przechodzi do edytora. Komunikat zawsze przez `aria-live`; fokus nigdy nie ginie na `body`.
- Kliknięcie w podglądzie to tylko skrót myszą; każdy element da się wybrać z klawiatury w strukturze.
- Stan nigdy tylko kolorem: badge ma wzór i słowo, linie błędu ikonę, kroki i zakładki licznik w nazwie dostępnej. Znaczniki marginesu są `aria-hidden`, bo tę samą informację niesie badge i lista.
- Podgląd: strona `h3`, sekcja `h4`. Przewijanie do elementu bez animacji przy `prefers-reduced-motion`.

## Poza zakresem

Edycja przez podgląd (przeciąganie), dodawanie i usuwanie pól oraz stron, zapis poprawek na serwerze, ponowna walidacja przez backend, historia zmian poza cofaniem edytora. Do osobnych issue.
