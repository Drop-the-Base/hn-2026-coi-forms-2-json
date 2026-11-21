# Propozycja nowego słownika: `DYSCYPLINY_SPORTOWE` (FR-E2)

## Wybór i uzasadnienie

Kandydaci z [analizy §6.4](analiza-i-charakterystyka-danych.md#64-rozszerzenia-punktowane-i-ich-pokrycie-przez-dane), sprawdzeni na formularzach 2–9:

| Kandydat | Gdzie w 2–9 | Ocena |
| --- | --- | --- |
| **Dyscypliny sportowe** | nr 9, sekcja „Dyscypliny sportowe”: zamknięta lista 20 pozycji (od „gimnastyka artystyczna” do „zapasy”) + „Inna dyscyplina”, poprzedzona wyborem rodzaju (zespołowa / indywidualna – inna / indywidualna – lekkoatletyka). Wielokrotny wybór („wybierz konkretne dyscypliny z listy”). | **wybrany** |
| Rasy psów | nr 7, „Rasa psa” jako wolny tekst; treść formularza dotyczy chartów (Prawo łowieckie), a tytuł ras agresywnych, więc lista jest niejednoznaczna | odrzucony |
| Tytuł władania nieruchomością | nr 8, poz. 1: 6 stałych opcji jednej gminy | odrzucony, wystarczy `options` w RADIO |
| Rodzaje podatków | nr 5 to materiał referencyjny, nie formularz 2–9 | poza zakresem |

Wszyscy kandydaci występują w jednym formularzu, więc wybraliśmy według danych: tylko dyscypliny mają w formularzu gotową listę wartości, naturalny drugi poziom (rodzaj) i wielokrotny wybór. Taka lista powtarza się w każdej gminie, która przyznaje stypendia sportowe, więc warto ją trzymać we wspólnym słowniku. Formularz nr 9 wymaga też „zaświadczenia wydanego przez Polski Związek Sportowy odpowiedni dla danej dyscypliny”, a słownik może podać nazwę tego związku.

## Nazwa

`DYSCYPLINY_SPORTOWE`. Wielkie litery i podkreślenia jak w `TERYT_4G_DOWODOWY`, liczba mnoga jak w `Kraje`.

## Struktura rekordu

| Pole | Typ | Przykład |
| --- | --- | --- |
| `kod` | string, unikalny | `PILKA_NOZNA` |
| `nazwa` (wartość zapisywana w polu) | string | `piłka nożna` |
| `rodzaj` (poziom 1) | `ZESPOLOWA` / `INDYWIDUALNA` | `ZESPOLOWA` |
| `zwiazekSportowy` | string | `Polski Związek Piłki Nożnej` |
| `aktywny` | bool | `true` |

Hierarchia ma 2 poziomy: rodzaj → dyscyplina. Przykłady: `ZESPOLOWA` → koszykówka, piłka ręczna, unihokej; `INDYWIDUALNA` → lekkoatletyka, łucznictwo, zapasy. Rodzaj „indywidualna – lekkoatletyka” z formularza zastępujemy dyscypliną `lekkoatletyka` w rodzaju `INDYWIDUALNA`, bo dziś ta sama wartość występuje na dwóch poziomach. „Inna dyscyplina” zostaje osobnym polem TEXT_FIELD z regułą SHOW, nie trafia do słownika.

## Zastosowanie w JSON

Formularz nr 9, zakładka „Dane sportowca”: pole wielokrotnego wyboru. Według reguł technicznych CHECKBOX może korzystać ze słownika i wtedy `options` jest puste. Fragment ma te same klucze co pola słownikowe we wzorcu nr 5:

```json
{
  "id": "<uuid>",
  "type": "CHECKBOX",
  "techName": "dyscypliny_sportowe",
  "title": "Dyscypliny sportowe",
  "description": "Wybierz dyscypliny, w których startuje kandydat",
  "dictionaryName": "DYSCYPLINY_SPORTOWE",
  "options": [],
  "multiLevelTree": true,
  "validation": [],
  "searchEnabled": true,
  "readOnly": false,
  "repeatingSectionGrid": [],
  "defaultValue": [],
  "states": [],
  "questionOrder": 0,
  "tooltipMessage": ""
}
```

`multiLevelTree: true` grupuje dyscypliny według `rodzaj`, tak jak TERYT grupuje adres. Nazwę słownika dopisujemy do listy słowników w konfiguracji (decyzja K-06). Dzięki temu generator może przypisać `dictionaryName` po rozpoznaniu pola o tytule „Dyscypliny sportowe”.

## Źródło danych i utrzymanie

- Źródło: ewidencja polskich związków sportowych prowadzona przez ministra właściwego do spraw kultury fizycznej (ustawa o sporcie). Jeden związek obejmuje jedną lub kilka dyscyplin, stąd pole `zwiazekSportowy`.
- Wersja startowa: 20 pozycji z formularza nr 9.
- Utrzymanie: właściciel słownika (COI) aktualizuje go po zmianach w ewidencji. Pozycji nie usuwamy, tylko ustawiamy `aktywny: false`, żeby złożone wnioski nadal miały poprawne wartości.
