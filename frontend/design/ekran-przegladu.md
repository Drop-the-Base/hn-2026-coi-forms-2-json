# Ekran przeglądu wyniku: [przeglad.html](przeglad.html)

Główny ekran pracy urzędnika (issue #48): widzi, co sprawdzić, poprawia JSON, ogląda formularz tak, jak zobaczy go wnioskodawca, i pobiera poprawioną wersję. Wymagania: [FR-T1](../../docs/requirements.md) (confidence, ocena ogólna, lista problemów), [FR-T2](../../docs/requirements.md) (edycja i pobieranie), [FR-E5](../../docs/requirements.md) (podgląd formularza), [FR-06](../../docs/requirements.md) (schemat), [NFR-06](../../docs/requirements.md), [NFR-15](../../docs/requirements.md). Wygląd: [DESIGN.md](../DESIGN.md).

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

## 1. Układ (≥ 64rem)

Ekran nie przewija się jako całość: stałe nagłówki, a pod nimi trzy obszary, każdy z własnym przewijaniem.

```
┌ pasek aplikacji ─────────────────────────────────────────────────────────────────────────────┐
│ ← Zadania                                                                                    │
│ Wniosek o ustalenie numeru porządkowego nieruchomości    Ocena ogólna [▨ Średnia 0,78]       │
│ plik.pdf, e52b8a07, wynik dostępny do 11:34              2 błędy, 5 do sprawdzenia [Pobierz JSON] │
├ Problem 3 z 7 ⚠ Do sprawdzenia  Niepewny typ pola… (ścieżka)  [█ Niska 0,41]  [‹ Poprzedni] [Następny ›] ┤  przyklejony
├──────────────┬──────────────────────────────┬──────────────────────────────────────────────┤
│ Problemy (7) │ JSON              [Formatuj] │ Podgląd formularza                           │
│ [Wszystkie▾] │ 129 █ { "x": 0, …            │ (1) Dane ⚠1 (2) Informacje o budynku ⚠3 …    │
│ ✕ Błąd …     │ 130 █   "field": {           │ Informacje o budynku                          │
│ ✕ Błąd …     │ 131 █     "id": "ef58…",     │ ┌ Lokalizacja budynku ────────────────────┐  │
│▐⚠ Do spr. …  │ 132 █     "type": "TEXT_FIELD"│ █│ Miejscowość [█ Niska 0,41]  ← bieżący   │  │
│ ⚠ Do spr. …  │ …                            │  │ Ulica                                    │  │
│ F8 następny  │ ✓ Zgodny ze schematem eUsługi│ █│ Numer ewidencyjny działki [█ Niska 0,52] │  │
└──────────────┴──────────────────────────────┴──────────────────────────────────────────────┘
  19rem            1fr                            1.1fr        █ = znacznik marginesu (sygnatura)
```

- Kolejność obszarów = kolejność pracy: co sprawdzić → gdzie poprawić → jak to wygląda.
- Między 64rem a 80rem lista problemów zwęża się, ale zostaje (pasek „Problem N z M” i tak prowadzi).

## 2. Nagłówek wyniku

| Element | Zachowanie |
|---|---|
| „← Zadania” | powrót do listy; przy niepobranych poprawkach najpierw dialog (§6) |
| tytuł | `title` z bieżącego JSON-a (zmienia się po edycji) |
| metadane | nazwa pliku, `job_id`, czas wygaśnięcia wyniku (TTL, NFR-06) |
| ocena ogólna | badge z `confidence.overall` |
| licznik | „2 błędy, 5 do sprawdzenia”; przy zerze „Brak problemów” |
| „Pobierz JSON” | jedyny główny przycisk; pobiera aktualną treść edytora jako `<techName-formularza>.json`. Wyłączony tylko, gdy JSON się nie parsuje albo nie przechodzi schematu, z powodem obok („Popraw 1 błąd schematu, aby pobrać.”). Błędy reguł R/S nie blokują: decyduje urzędnik. Bez dialogu przed pobraniem. |

## 3. Pasek „Problem N z M” (przyklejony)

Pokazuje tylko następną decyzję: pozycję, rodzaj (ikona + słowo), opis z `message`, ścieżkę elementu (strona, sekcja, pole), badge pewności, „Poprzedni” / „Następny” (`F8` / `Shift+F8`, `aria-keyshortcuts`). Kolejność: najpierw błędy (reguły, schemat), potem elementy poniżej progu od najniższej pewności. Po ostatnim „Następny” wraca do pierwszego z komunikatem „To był ostatni problem. Wracam do pierwszego.” Przy braku problemów pasek mówi „Brak problemów do sprawdzenia” i zachęca do przejrzenia podglądu.

## 4. Lista problemów i przejście do elementu

- `<ol>` przycisków, jeden wiersz = jeden problem: rodzaj, opis, ścieżka, badge (dla `check`). Bieżący wiersz: tło `accent-subtle`, wewnętrzny pasek 3 px `accent`, `aria-current="true"`.
- Filtr „Pokaż”: Wszystkie / Błędy / Niska pewność.
- Kliknięcie lub Enter na wierszu (to samo robi pasek i `F8`):
  1. podgląd przełącza stronę na tę z elementem, przewija do niego i zaznacza go (obrys `accent`, tło `accent-subtle`);
  2. edytor przewija do obiektu elementu, podświetla jego linie (`code-current`) i stawia kursor na pierwszej linii;
  3. **fokus trafia do edytora**, bo tam się poprawia; `aria-live`: „Problem 3 z 7: Miejscowość, strona Informacje o budynku, pewność niska 0,41.”;
  4. `Esc` w edytorze albo `Alt+P` wraca fokusem do wiersza listy.
- Element usunięty w edytorze: wiersz z tekstem `muted` „Element usunięty z JSON-a”, przycisk nieaktywny.
- Po edycji: błędy schematu i parsowania liczymy lokalnie od razu. Reguły R/S i confidence liczy backend, więc zmienione elementy dostają dopisek „zmienione, nieprzeliczone”. Ponownej walidacji przez backend nie projektujemy (brak endpointu, YAGNI).

## 5. Edytor JSON

- CodeMirror 6 (ADR-0011), `--font-mono` 14 px, numery linii, zwijanie bloków (zwinięty obiekt pokazuje etykietę pola: „Ulica, 14 linii”), kolory składni z tokenów `code-*`.
- Rynna: numer linii, **znacznik marginesu** (pełny / kreskowany przy liniach elementu poniżej progu), kolumna ikon błędu schematu.
- Pasek stanu pod edytorem (`aria-live="polite"`, podpięty `aria-describedby`):

| Stan | Pasek | „Pobierz JSON” |
|---|---|---|
| poprawny | „Zgodny ze schematem eUsługi” (`success`) | aktywny |
| błąd składni | „Błąd składni w linii 42: brak przecinka.” (`error`) | wyłączony + powód |
| niezgodny ze schematem | „1 niezgodność ze schematem” + lista „Linia 132: „type” ma niedozwoloną wartość „TEXT_FELD”. Czy chodziło o „TEXT_FIELD”?” | wyłączony + powód |

  Linia błędu: ikona ✕ w rynnie i falista linia `error` pod tekstem. „Linia 132” w komunikacie to link, który stawia tam kursor.
- Walidacja lokalnie względem `importowanyPlikJsonSchemat` z poprawką literówki `repeatingSectionGrid` (K-09), ok. 300 ms po ostatnim klawiszu.
- Edytor nie więzi fokusu: `Esc`, potem `Tab` wychodzi (opis w nazwie dostępnej regionu).
- „Formatuj” formatuje cały dokument; jest w historii cofania edytora.

## 6. Podgląd formularza (FR-E5)

- Render tylko do odczytu, w chłodnej palecie `eu-*` odwzorowanej z wizualizacji COI: niebiesko-szare tło, białe karty sekcji, etykieta nad polem, granatowy przycisk „Dalej”. Podpis „tak zobaczy go wnioskodawca w eUsłudze”.
- Kroki stron według `flow.links`, nie kolejności w `tabs[]`; bieżąca `aria-current="step"`; przy stronie z problemami ikona i liczba, w nazwie dostępnej „Strona 2, Informacje o budynku, 3 problemy”. `flow` niespójny: kroki w kolejności `tabs[]` i komunikat `warning` „Przepływ stron jest niespójny. Strony pokazano w kolejności z pliku.”
- Każda karta ma po lewej **margines pewności** (28 px): znacznik przy polu albo sekcji poniżej progu, długi jak element. Obok etykiety badge. Kliknięcie pola zaznacza jego obiekt w edytorze (bez przenoszenia fokusu).
- Typy pól: TEXT_FIELD, NUMBER, DATEPICKER → pole; TEXTAREA → pole wieloliniowe; SELECT → lista; RADIO, CHECKBOX → grupy; FILE_UPLOADER → „Dodaj lub przeciągnij plik” (nieaktywny) z limitami jak w eUsłudze; TEXT_BLOCK, INFO_SECTION → tekst; CONSENT_SECTION → checkbox zgody. Nieznany typ: ramka `rule` i „Nieobsługiwany typ pola: X”.
- Kontrolki RADIO i CHECKBOX działają, żeby sprawdzić stany `SHOW` (FR-E3), np. „Innej osoby” odsłania „Dane innej osoby”. Wartości nie trafiają do JSON-a. „Wróć” / „Dalej” przełączają strony podglądu.
- Odświeżenie po każdej zmianie dającej poprawny JSON. Przy błędzie składni lub schematu zostaje ostatni poprawny render z komunikatem `info` „Podgląd sprzed ostatniej zmiany: JSON nie przechodzi schematu.”
- Wydajność: render tylko bieżącej strony formularza.

## 7. Wyjście z niepobranymi poprawkami

Zmiany po ostatnim pobraniu + próba wyjścia („Zadania”, „Wyloguj”, zamknięcie karty przez `beforeunload`): `<dialog>` „Masz niepobrane poprawki. Zmieniłeś JSON po ostatnim pobraniu. Po wyjściu poprawki przepadną, bo serwer ich nie przechowuje.” Akcje: „Zostań” (główna, domyślny fokus) i „Wyjdź bez pobierania” (wariant niszczący, obrys `error`). To jedyny dialog na ekranie.

## 8. Wąski ekran (< 64rem)

- Nagłówek się układa w kolumnę, „Pobierz JSON” na pełną szerokość.
- Pasek problemu zostaje przyklejony, opis przechodzi do drugiej linii.
- Obszary stają się zakładkami (`role="tablist"`, przyklejone pod paskiem problemu): **Podgląd** (domyślna), **JSON**, **Problemy N**. Przejście do problemu otwiera zakładkę JSON z zaznaczonym elementem. Błąd schematu przy otwartym podglądzie: ikona ✕ na zakładce JSON i komunikat nad podglądem.
- Bez JavaScriptu obszary stoją jeden pod drugim. Strona nie przewija się poziomo; długie linie edytora przewijają się w jego kontenerze.

## 9. Dostępność (NFR-15)

- Skip link „Przejdź do edytora”. Tabulacja: nagłówek → pasek problemu → lista → edytor → podgląd.
- Skróty: `F8` / `Shift+F8` następny / poprzedni problem, `Alt+P` lista, `Alt+E` edytor, `Alt+F` podgląd; opis w stopce listy.
- Fokus po przejściu do problemu zawsze w edytorze, z komunikatem `aria-live`; nigdy nie ginie na `body`.
- Stan nigdy tylko kolorem: badge ma wzór i słowo, linie błędu ikonę, kroki i zakładki licznik w nazwie dostępnej. Znaczniki marginesu są `aria-hidden`, bo tę samą informację niesie badge i lista.
- Podgląd: strona `h3`, sekcja `h4`. Przewijanie do elementu bez animacji przy `prefers-reduced-motion`.

## Poza zakresem

Edycja przez podgląd (przeciąganie, panel właściwości pola), zapis poprawek na serwerze, ponowna walidacja przez backend, historia zmian poza cofaniem edytora, porównanie z oryginalnym plikiem obok. Do osobnych issue.
