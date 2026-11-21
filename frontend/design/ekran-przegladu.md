# Ekran przeglądu wyniku

Główny ekran pracy urzędnika: poprawia JSON wygenerowany przez AI, widzi, jak formularz wygląda w eUsłudze, i pobiera poprawioną wersję. Wymagania: [FR-T1](../../docs/requirements.md) (confidence, ocena ogólna, lista problemów), [FR-T2](../../docs/requirements.md) (edycja i pobieranie), [FR-E5](../../docs/requirements.md) (podgląd formularza), [NFR-15](../../docs/requirements.md) (WCAG 2.1 AA). Wygląd: wyłącznie tokeny i komponenty z [DESIGN.md](../DESIGN.md).

Założenia robocze (do potwierdzenia z backendem):
- API zwraca obok `form` osobno: `confidence.overall`, `confidence.elements` (mapa `id` strony/pola → 0–1) i `issues[]` (`ruleId`, `message`, `elementId`, `severity`). Confidence **nie trafia** do pobieranego JSON-a, bo plik musi przejść schemat eUsługi.
- Próg podświetlenia `CONFIDENCE_REVIEW_THRESHOLD` = 0,85, czyli podświetlamy poziom średni i niski z DESIGN.md §1.

## 1. Układ na szerokim ekranie (≥ 1024px)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ ← Zadania   Wniosek o ustalenie numeru porządkowego nieruchomości                        │  tytuł --text-2xl
│ Ocena ogólna: [! Średnia 0,78]  Problemy: 2 błędy, 5 do sprawdzenia   [Problemy (7) ▾]  [⤓ Pobierz JSON] │  pasek wyniku
├──────────────────────────────────────────┬───────────────────────────────────────────────┤
│ Edytor JSON                     [Formatuj]│ Podgląd formularza                            │
│ ┌──────────────────────────────────────┐ │ ┌──────────────────────────────────────────┐  │
│ │ 1  {                                 │ │ │ (1) Dane › (2) Informacje o budynku ›     │  │  nawigacja wg flow
│ │ 2    "title": "Wniosek o ustalenie…",│ │ │ (3) Kontakt z urzędem › (4) Strona końc.  │  │
│ │ 3    "tabs": [                       │ │ ├──────────────────────────────────────────┤  │
│ │ 4      {                             │ │ │ Organ, do którego jest składany wniosek  │  │  sekcja
│ │ 5        "title": "Dane",            │ │ │  Wybierz urząd (wymagane)                │  │
│ │ …                                    │ │ │  [ Urząd Miasta …                   ▾ ]  │  │
│▌│41        "label": "Numer działki",   │ │ │                                          │  │
│▌│42        "type": "TEXT_FIELD",  ✕    │ │ │ Podmiot wniosku                          │  │
│ │ …                                    │ │ │  Składam wniosek w imieniu: (wymagane)   │  │
│ └──────────────────────────────────────┘ │ │  ( ) Swoim  ( ) Innej osoby  ( ) Osoby…  │  │
│ ✓ Zgodny ze schematem                    │ │                                          │  │
│                                          │ │▌Twoje dane          [! Średnia 0,71]     │  │  pole/sekcja < progu
│                                          │ │▌ Imię (wymagane)                          │  │
│                                          │ │▌ [ Jan                               ]   │  │
│                                          │ │                                          │  │
│                                          │ │        [Poprzednia strona] [Następna strona]│ │
│                                          │ └──────────────────────────────────────────┘  │
└──────────────────────────────────────────┴───────────────────────────────────────────────┘
```

- Kolumny 50/50, każda przewija się sama; pasek wyniku zostaje przyklejony u góry (`position: sticky`).
- `▌` = lewa krawędź 4px `confidence-<poziom>-border` (DESIGN.md §5, pole z niskim confidence). Tak samo w edytorze: znacznik na marginesie przy liniach elementu.

### Pasek wyniku

| Element | Komponent | Zachowanie |
|---|---|---|
| „Ocena ogólna” | badge confidence z wartością | `confidence.overall` |
| licznik problemów | tekst `--text-sm` | „2 błędy, 5 do sprawdzenia”; przy zerze: „Brak problemów” |
| „Problemy (7)” | przycisk `secondary`, `aria-expanded` | otwiera/zamyka listę problemów (§2) |
| „Pobierz JSON” | przycisk `primary` (jedyny na ekranie) | pobiera aktualną treść edytora jako `<techName-formularza>.json`; wyłączony, gdy JSON nie parsuje się lub nie przechodzi schematu (§4) |

Pobranie przy błędach reguł R/S (nie schematu) jest dozwolone: urzędnik decyduje. Przed pobraniem nie ma dialogu, żeby nie spowalniać pracy.

## 2. Lista problemów

Panel rozwijany pod paskiem wyniku, nad kolumnami (nie zasłania edytora, spycha go w dół). Domyślnie otwarty, jeśli są błędy.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Problemy (7)                                                Pokaż: [Wszystkie ▾]  [Zwiń] │
├──────────┬──────────────────────────────────────────────────┬─────────────────┬──────────┤
│ Rodzaj   │ Opis                                             │ Element         │ Pewność  │
├──────────┼──────────────────────────────────────────────────┼─────────────────┼──────────┤
│ ✕ Błąd   │ Strona końcowa zawiera pole do wypełnienia (R-…) │ Strona końcowa  │          │
│ ✕ Błąd   │ techName „imie” występuje dwa razy               │ Dane › Imię     │          │
│ ! Do spr.│ Niska pewność typu pola                          │ Numer działki   │ ✕ Niska 0,34 │
│ ! Do spr.│ Niepewna etykieta                                │ Twoje dane      │ ! Średnia 0,71│
│ …        │                                                  │                 │          │
└──────────┴──────────────────────────────────────────────────┴─────────────────┴──────────┘
```

- Tabela z DESIGN.md §5. Kolejność: najpierw błędy (naruszone reguły i schemat), potem elementy poniżej progu od najniższej pewności.
- Kolumna „Rodzaj”: ikona + tekst (`error` „Błąd”, `warning` „Do sprawdzenia”), nigdy sam kolor.
- Filtr „Pokaż”: Wszystkie / Błędy / Niska pewność.
- W komórce „Element” jest przycisk `ghost` z nazwą elementu (nazwa dostępna: „Przejdź do: Numer działki”); kliknięcie w dowolne miejsce wiersza robi to samo, ale klawiaturą fokus dostaje tylko ten przycisk. Strzałki góra/dół przechodzą między wierszami.

### Przejście do elementu

Kliknięcie lub Enter na wierszu:
1. Podgląd przełącza się na stronę z elementem, przewija do niego i zaznacza go (tło `primary-subtle`, lewa krawędź 3px `primary`, jak zaznaczony wiersz tabeli).
2. Edytor przewija do linii elementu (`"id"` lub `"techName"`), zaznacza cały obiekt elementu i stawia w nim kursor.
3. **Fokus trafia do edytora** na początek obiektu, bo tam urzędnik poprawia. Komunikat w regionie `aria-live="polite"`: „Przeniesiono do: Numer działki, strona Dane. Niska pewność 0,34.”
4. `Esc` w edytorze lub skrót `Alt+P` wraca fokusem do tego samego wiersza listy problemów.

Element bez dopasowania (usunięty w edytorze): wiersz wyszarzony (`disabled-text`), opis „Element usunięty z JSON-a”.

Lista odświeża się lokalnie po każdej poprawnej zmianie w edytorze tylko dla błędów schematu i parsowania. Reguły R/S i confidence liczy backend; po edycji wiersze, których element zmieniono, dostają dopisek „zmienione, nieprzeliczone” (`text-muted`). Ponownej walidacji przez backend nie projektujemy tutaj (YAGNI do czasu endpointu).

## 3. Podgląd formularza (FR-E5)

Render tylko do odczytu, ale wyglądem bliski eUsłudze z wizualizacji w `data/…/wizualizacja formularza po cyfryzacji.docx`: strony tematyczne, sekcje z nagłówkiem, pola z etykietą nad polem, przyciski „Poprzednia strona” / „Następna strona”.

- Nawigacja po stronach wg `flow.links` (źródło → cel), nie wg kolejności w `tabs[]`. Pasek kroków: numer + tytuł strony; bieżąca ma `aria-current="step"`. Strona z problemem ma przy numerze ikonę ✕ lub ! i licznik w nazwie dostępnej: „Strona 1, Dane, 2 problemy”.
- `flow` niespójny (strona poza łańcuchem, cykl): kroki w kolejności `tabs[]`, nad podglądem karta stanu `warning` „Przepływ stron jest niespójny. Strony pokazano w kolejności z pliku.”
- Pola wg typu: TEXT_FIELD/NUMBER/DATEPICKER → pole formularza, TEXTAREA → pole wieloliniowe, SELECT → lista, RADIO/CHECKBOX → grupy, FILE_UPLOADER → przycisk „Dodaj plik” (nieaktywny), TEXT_BLOCK/INFO_SECTION → tekst, CONSENT_SECTION → checkbox ze zgodą. Nieznany typ: ramka `border`, tekst „Nieobsługiwany typ pola: X”.
- Kontrolki są interaktywne tylko po to, żeby sprawdzić stany `SHOW` (np. „Innej osoby” odsłania sekcje „Dane innej osoby”, „Pełnomocnictwo”). Wartości nie trafiają do JSON-a.
- Pole lub sekcja poniżej progu: lewa krawędź 4px + badge confidence obok etykiety (DESIGN.md §5). Obok badge przycisk `ghost` „Dlaczego?”, który otwiera wiersz problemu na liście (to samo przejście co w §2, ale w drugą stronę: zaznacza wiersz i element w edytorze, fokus zostaje w podglądzie).
- Kliknięcie dowolnego pola w podglądzie zaznacza jego obiekt w edytorze (bez przenoszenia fokusu).
- Podgląd odświeża się po każdej zmianie, która daje poprawny JSON (z opóźnieniem ok. 300 ms od ostatniego klawisza). Przy błędzie składni zostaje ostatni poprawny render z paskiem `info` „Podgląd sprzed ostatniej zmiany: JSON zawiera błąd.”

## 4. Edytor JSON i błąd walidacji schematu

Edytor z `--font-mono`, numeracją linii, zwijaniem bloków. Pod nim pasek stanu:

| Stan | Pasek pod edytorem | „Pobierz JSON” |
|---|---|---|
| poprawny | `success`: „✓ Zgodny ze schematem” | aktywny |
| błąd składni | `error`: „✕ Błąd składni w linii 42: brak przecinka.” | wyłączony |
| niezgodny ze schematem | `error`: „✕ 2 niezgodności ze schematem” + lista | wyłączony |

```
│ │40      {                                     │
│ │41        "label": "Numer działki",           │
│▌│42        "type": "TEXT_FELD",           ✕    │  linia z błędem: krawędź error + ikona na marginesie
│ │43        "techName": "numer_dzialki"         │
│ └──────────────────────────────────────────────┘
│ ┌ ✕ 2 niezgodności ze schematem ───────────────┐
│ │ Linia 42: „type” ma niedozwoloną wartość     │  przycisk: przejdź do linii
│ │   „TEXT_FELD”. Dozwolone: TEXT_FIELD, NUMBER…│
│ │ Linia 88: brak wymaganego pola „techName”.   │
│ └──────────────────────────────────────────────┘
```

- Walidacja lokalna względem `importowanyPlikJsonSchemat`, po każdej zmianie (to samo opóźnienie co podgląd).
- Komunikat mówi, co poprawić, nie tylko co jest źle. Lista podpięta do edytora przez `aria-describedby`; zmiana liczby błędów ogłaszana w `aria-live="polite"`.
- Przycisk „Pobierz JSON” wyłączony ma obok tekst `text-muted` „Popraw błędy w edytorze, aby pobrać”, żeby powód był widoczny, nie tylko w podpowiedzi.
- Opuszczenie ekranu z niezapisanymi zmianami (zmiany po ostatnim pobraniu): dialog „Masz niepobrane poprawki. Wyjść bez pobierania?” [Zostań] (primary) [Wyjdź] (secondary). Bez tego urzędnik traci pracę.

## 5. Wąski ekran (< 1024px)

Kolumny zamieniają się w zakładki (`role="tablist"`). Pasek wyniku zostaje u góry, przycisk „Pobierz JSON” na pełną szerokość pod oceną.

```
┌──────────────────────────────────┐
│ ← Zadania                        │
│ Wniosek o ustalenie numeru…      │
│ Ocena: [! Średnia 0,78]          │
│ [Problemy (7) ▾]                 │
│ [⤓        Pobierz JSON         ] │
├──────────────────────────────────┤
│ [ Podgląd ✕2 ] [ Edytor ] [ Problemy 7 ] │
├──────────────────────────────────┤
│ (1) Dane ▾   strona 1 z 4        │  kroki zwinięte do listy
│                                  │
│ Organ, do którego jest składany… │
│  [ Urząd Miasta …           ▾ ]  │
│ ▌Twoje dane   [! Średnia 0,71]   │
│ …                                │
│ [Poprzednia]      [Następna]     │
└──────────────────────────────────┘
```

- Zakładki: „Podgląd” (domyślna, bo urzędnik najpierw ogląda formularz), „Edytor”, „Problemy”. Licznik problemów w nazwie zakładki („Problemy, 7”).
- Przejście do problemu otwiera zakładkę „Edytor” z zaznaczonym elementem i fokusem w nim; z badge „Dlaczego?” w podglądzie otwiera zakładkę „Problemy” na danym wierszu.
- Błąd schematu przy aktywnym „Podglądzie”: ikona ✕ na zakładce „Edytor” i ten sam pasek `info` nad podglądem.
- Strona nie przewija się poziomo; długie linie w edytorze zawijają się albo przewijają w jego kontenerze.

## 6. Dostępność (NFR-15)

- Kolejność tabulacji: pasek wyniku → lista problemów (gdy otwarta) → edytor → podgląd. Link „Przejdź do edytora” jako pierwszy element strony (skip link).
- Edytor nie więzi fokusu: `Tab` wstawia wcięcie tylko po włączeniu trybu wcięć; domyślnie `Esc`, potem `Tab` wychodzi z edytora. Informacja o tym w opisie edytora (`aria-describedby`).
- Skróty: `Alt+P` lista problemów, `Alt+E` edytor, `Alt+F` podgląd, `F8` / `Shift+F8` następny / poprzedni problem (przejście jak w §2). Lista skrótów pod przyciskiem `ghost` „Skróty klawiszowe”.
- Fokus po przejściu do problemu: zawsze w miejscu edycji (edytor), z komunikatem `aria-live`; nigdy nie ginie na `body`.
- Stan nigdy nie jest tylko kolorem: badge ma słowo poziomu, linie z błędem mają ikonę, zakładki i kroki mają licznik w nazwie dostępnej.
- Podgląd ma nagłówki stron (`h2`) i sekcji (`h3`), żeby czytnik pozwalał po nich skakać.
- Przewijanie do elementu bez animacji przy `prefers-reduced-motion: reduce`.

## Poza zakresem

Edycja formularza przez podgląd (przeciągnij-upuść, formularz właściwości pola), zapis poprawek na serwerze, ponowna walidacja przez backend, historia zmian i cofanie poza tym, co daje edytor. Do osobnych issue, gdy będą potrzebne.
