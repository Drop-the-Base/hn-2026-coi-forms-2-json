# System wizualny frontendu

Panel urzędnika, który poprawia wynik AI ([FR-T1](../docs/requirements.md), [FR-T2](../docs/requirements.md)). Ton: rzeczowy, urzędowy, czytelny. Cel dostępności: WCAG 2.1 AA ([NFR-15](../docs/requirements.md)). Stack: shadcn/ui + Tailwind ([ADR-0011](../docs/adr/0011-frontend-react-vite.md)); tokeny poniżej to zmienne CSS, które shadcn/Tailwind czytają bez dodatkowych bibliotek.

Zasady:
- Kolor nigdy nie jest jedynym nośnikiem informacji: stan zawsze ma też tekst, a w miarę możliwości ikonę.
- Jeden kolor akcentu (granat). Kolory semantyczne tylko dla stanów, nie do dekoracji.
- Gęstość średnia: urzędnik przegląda dużo pól, więc bez wielkich odstępów, ale z wyraźnym rytmem.
- Tylko tryb jasny.

## 1. Kolory

| Token | Hex | Użycie |
|---|---|---|
| `--color-bg` | `#FFFFFF` | tło strony, pola formularza, karty |
| `--color-surface` | `#F4F5F7` | tło sekcji, nagłówek tabeli, hover wiersza |
| `--color-text` | `#1A1F2B` | tekst główny |
| `--color-text-muted` | `#4A5263` | etykiety pomocnicze, opisy, metadane |
| `--color-border` | `#D5D9E0` | podziały dekoracyjne (linie tabeli, ramka karty), bez wymogu kontrastu |
| `--color-border-strong` | `#767E8C` | ramka pola formularza, checkboxa, przycisku secondary |
| `--color-primary` | `#0B4F9C` | przycisk główny, link, fokus |
| `--color-primary-hover` | `#083D79` | hover/active przycisku głównego |
| `--color-primary-subtle` | `#E7F0FA` | hover przycisku secondary, zaznaczony wiersz |
| `--color-on-primary` | `#FFFFFF` | tekst na `primary` i `danger` |
| `--color-focus` | `#0B4F9C` | pierścień fokusu |
| `--color-disabled-bg` | `#ECEEF1` | tło elementu wyłączonego |
| `--color-disabled-text` | `#5F6673` | tekst elementu wyłączonego |

Kolory semantyczne: tekst/ikona + tło komunikatu + ramka (dla elementów UI na białym tle).

| Stan | Tekst (`--color-<stan>`) | Tło (`--color-<stan>-bg`) | Ramka (`--color-<stan>-border`) |
|---|---|---|---|
| `error` | `#B3261E` | `#FDECEA` | `#B3261E` |
| `warning` | `#7A4A00` | `#FFF4E0` | `#A86500` |
| `success` | `#1E6B34` | `#E8F5EB` | `#2E7D45` |
| `info` | `#0B4F9C` | `#E7F0FA` | `#0B4F9C` |

Przycisk `danger`: tło `--color-error`, hover `#8C1D17` (`--color-error-hover`).

### Confidence (FR-T1)

Trzy poziomy, mapowane na kolory semantyczne, żeby nie mnożyć palety. Progi są **robocze**, do potwierdzenia, gdy backend ustali skalę.

| Poziom | Zakres | Kolory | Ikona | Tekst w badge |
|---|---|---|---|---|
| wysoki | ≥ 0,85 | `success` | ✓ (ptaszek) | `Wysoka 0,92` |
| średni | 0,60–0,84 | `warning` | ! (trójkąt) | `Średnia 0,71` |
| niski | < 0,60 | `error` | ✕ (koło z krzyżykiem) | `Niska 0,34` |

## 2. Typografia

Systemowy stos fontów: zero dodatkowych zależności i plików, pełne polskie znaki, natywny rendering. Gdy zespół zechce jednolity krój na wszystkich systemach, kandydatem jest Inter (OFL 1.1), ale to wymaga ADR.

- `--font-sans`: `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
- `--font-mono`: `ui-monospace, "SF Mono", "Cascadia Mono", Consolas, "Liberation Mono", monospace` (edytor JSON, identyfikatory pól)

| Token | Rozmiar | Wysokość linii | Grubość | Użycie |
|---|---|---|---|---|
| `--text-xs` | 0.75rem (12px) | 1rem | 500 | badge, metadane |
| `--text-sm` | 0.875rem (14px) | 1.25rem | 400 | tabela, etykiety, opisy pól |
| `--text-base` | 1rem (16px) | 1.5rem | 400 | tekst główny, pola formularza |
| `--text-lg` | 1.125rem (18px) | 1.75rem | 600 | nagłówek karty |
| `--text-xl` | 1.25rem (20px) | 1.75rem | 600 | nagłówek sekcji |
| `--text-2xl` | 1.5rem (24px) | 2rem | 600 | tytuł strony |

Minimum dla tekstu ciągłego: 14px. Liczby w tabelach: `font-variant-numeric: tabular-nums`. Rozmiary w `rem`, żeby działało powiększenie tekstu do 200% (WCAG 1.4.4).

## 3. Odstępy, promienie, cienie

Skala odstępów w krokach 4px.

| Token | Wartość | Typowe użycie |
|---|---|---|
| `--space-1` | 0.25rem (4px) | ikona–tekst |
| `--space-2` | 0.5rem (8px) | wnętrze badge, odstęp etykieta–pole |
| `--space-3` | 0.75rem (12px) | padding komórki tabeli, pola |
| `--space-4` | 1rem (16px) | padding przycisku poziomo, odstęp pól |
| `--space-6` | 1.5rem (24px) | padding karty |
| `--space-8` | 2rem (32px) | odstęp sekcji |

| Token | Wartość | Użycie |
|---|---|---|
| `--radius-sm` | 0.25rem (4px) | badge, checkbox |
| `--radius-md` | 0.375rem (6px) | przycisk, pole |
| `--radius-lg` | 0.5rem (8px) | karta, okno dialogowe |
| `--shadow-sm` | `0 1px 2px rgb(26 31 43 / 0.08)` | karta |
| `--shadow-md` | `0 4px 12px rgb(26 31 43 / 0.12)` | menu rozwijane, dialog |

Cienie są wyłącznie dekoracyjne: granicę elementu zawsze wyznacza ramka.

## 4. Blok CSS

```css
:root {
  /* kolory bazowe */
  --color-bg: #FFFFFF;
  --color-surface: #F4F5F7;
  --color-text: #1A1F2B;
  --color-text-muted: #4A5263;
  --color-border: #D5D9E0;
  --color-border-strong: #767E8C;
  --color-primary: #0B4F9C;
  --color-primary-hover: #083D79;
  --color-primary-subtle: #E7F0FA;
  --color-on-primary: #FFFFFF;
  --color-focus: #0B4F9C;
  --color-disabled-bg: #ECEEF1;
  --color-disabled-text: #5F6673;

  /* kolory semantyczne */
  --color-error: #B3261E;
  --color-error-hover: #8C1D17;
  --color-error-bg: #FDECEA;
  --color-error-border: #B3261E;
  --color-warning: #7A4A00;
  --color-warning-bg: #FFF4E0;
  --color-warning-border: #A86500;
  --color-success: #1E6B34;
  --color-success-bg: #E8F5EB;
  --color-success-border: #2E7D45;
  --color-info: #0B4F9C;
  --color-info-bg: #E7F0FA;
  --color-info-border: #0B4F9C;

  /* confidence = aliasy stanów */
  --color-confidence-high: var(--color-success);
  --color-confidence-high-bg: var(--color-success-bg);
  --color-confidence-high-border: var(--color-success-border);
  --color-confidence-medium: var(--color-warning);
  --color-confidence-medium-bg: var(--color-warning-bg);
  --color-confidence-medium-border: var(--color-warning-border);
  --color-confidence-low: var(--color-error);
  --color-confidence-low-bg: var(--color-error-bg);
  --color-confidence-low-border: var(--color-error-border);

  /* typografia */
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", "Cascadia Mono", Consolas, "Liberation Mono", monospace;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;

  /* odstępy */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  /* promienie i cienie */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --shadow-sm: 0 1px 2px rgb(26 31 43 / 0.08);
  --shadow-md: 0 4px 12px rgb(26 31 43 / 0.12);

  /* fokus */
  --focus-ring: 0 0 0 2px var(--color-bg), 0 0 0 4px var(--color-focus);
}
```

Fokus: `:focus-visible { outline: none; box-shadow: var(--focus-ring); }`. Biały odstęp 2px + granatowy pierścień 2px jest widoczny na białym tle, na `surface` i na przycisku `primary` (pierścień leży na białym odstępie, nie na granacie). Nigdy `outline: none` bez zamiennika.

## 5. Komponenty bazowe

Wspólne dla wszystkich interaktywnych: minimalny obszar kliknięcia 2.5rem (40px) wysokości, `cursor: not-allowed` i brak hovera w stanie wyłączonym, fokus jak w §4, przejścia ≤ 150 ms i wyłączone przy `prefers-reduced-motion: reduce`.

### Przycisk

Wysokość 2.5rem, padding `0 var(--space-4)`, `--radius-md`, `--text-sm` 600. Ikona po lewej, odstęp `--space-2`. Etykieta to czasownik: „Wgraj plik”, „Pobierz JSON”, „Zapisz poprawki”.

| Wariant | Spoczynek | Hover / active | Kiedy |
|---|---|---|---|
| `primary` | tło `primary`, tekst `on-primary` | tło `primary-hover` | jedna główna akcja na ekranie |
| `secondary` | tło `bg`, tekst `primary`, ramka 1px `border-strong` | tło `primary-subtle` | akcje poboczne |
| `ghost` | bez tła i ramki, tekst `primary` | tło `primary-subtle` | akcje w wierszu tabeli, w pasku narzędzi |
| `danger` | tło `error`, tekst `on-primary` | tło `error-hover` | usunięcie, odrzucenie wyniku |

- Focus: `--focus-ring`.
- Disabled: tło `disabled-bg`, tekst `disabled-text`, bez ramki (dla `secondary` ramka `border`); atrybut `disabled`, nie sama klasa.
- Ładowanie: spinner zamiast ikony, etykieta zostaje („Wgrywanie…”), `aria-busy="true"`, przycisk zablokowany.

### Pole formularza

Etykieta nad polem (`--text-sm` 600, `text`), opis pod etykietą (`--text-sm`, `text-muted`), pole wysokości 2.5rem, padding `0 var(--space-3)`, tło `bg`, ramka 1px `border-strong`, `--radius-md`, tekst `--text-base`. Placeholder nie zastępuje etykiety.

| Stan | Wygląd |
|---|---|
| hover | ramka `text-muted` |
| focus | ramka `primary` + `--focus-ring` |
| disabled | tło `disabled-bg`, tekst `disabled-text`, ramka `border` |
| tylko do odczytu | tło `surface`, ramka `border`, tekst `text` |
| error | ramka 2px `error`, pod polem komunikat `error` z ikoną ✕ i treścią „co poprawić”, `aria-invalid="true"`, komunikat podpięty przez `aria-describedby` |
| niski confidence | lewa krawędź 4px `confidence-low-border` + badge obok etykiety (patrz niżej); pole dalej edytowalne |

Wymagane: dopisek „(wymagane)” przy etykiecie, nie sama gwiazdka.

### Karta

Tło `bg`, ramka 1px `border`, `--radius-lg`, `--shadow-sm`, padding `--space-6`. Nagłówek `--text-lg` 600, opcjonalnie badge i akcje (`ghost`) po prawej. Karta klikalna w całości: hover ramka `border-strong`, focus `--focus-ring`; w środku nie ma wtedy innych przycisków. Karta stanu (np. błąd przetwarzania): tło `<stan>-bg`, lewa krawędź 4px `<stan>-border`, ikona i tytuł w kolorze `<stan>`.

### Tabela

Pełna szerokość, `--text-sm`, padding komórki `--space-3`. Nagłówek: tło `surface`, tekst `text` 600, dolna linia 1px `border-strong`. Wiersze: dolna linia 1px `border`, bez zebry. Liczby i confidence wyrównane do prawej, `tabular-nums`.

| Stan wiersza | Wygląd |
|---|---|
| hover | tło `surface` |
| zaznaczony | tło `primary-subtle`, lewa krawędź 3px `primary`, `aria-selected="true"` |
| focus (nawigacja klawiaturą) | `--focus-ring` na wierszu lub komórce |
| błąd / niski confidence | badge w kolumnie „Pewność” + ikona przy nazwie pola; tła wiersza nie barwimy, żeby nie konkurowało z zaznaczeniem |
| pusta tabela | jeden wiersz z tekstem `text-muted`: co zrobić, np. „Brak zadań. Wgraj pierwszy formularz.” |

Sortowalne kolumny: przycisk w nagłówku, `aria-sort`. Na wąskim ekranie tabela przewija się poziomo w swoim kontenerze, strona nie.

### Badge confidence

Inline, `--radius-sm`, padding `0.125rem var(--space-2)`, `--text-xs` 500, tło `confidence-<poziom>-bg`, tekst `confidence-<poziom>`, ramka 1px `confidence-<poziom>-border`. Zawartość: ikona (`aria-hidden="true"`) + słowo poziomu + wartość z przecinkiem dziesiętnym, np. „✕ Niska 0,34”. Etykieta dla czytnika: `aria-label="Pewność: niska, 0,34"`. Badge nie jest interaktywny; jeśli ma tłumaczyć powód (lista problemów z FR-T1), robi to osobny przycisk `ghost` „Dlaczego?” obok.

Ten sam badge (bez wartości liczbowej, jeśli brak miejsca) służy do oceny ogólnej wyniku w nagłówku karty zadania.

## 6. Kontrast (zmierzony)

Wzór WCAG 2.1 (luminancja względna), policzone skryptem, nie na oko. Próg 4.5:1 dla tekstu, 3:1 dla elementów UI (ramki, fokus).

| Para | Tekst / UI | Tło | Wynik | Próg |
|---|---|---|---|---|
| tekst / tło | `#1A1F2B` | `#FFFFFF` | 16.47:1 | 4.5:1 |
| tekst / powierzchnia | `#1A1F2B` | `#F4F5F7` | 15.10:1 | 4.5:1 |
| tekst pomocniczy / tło | `#4A5263` | `#FFFFFF` | 7.84:1 | 4.5:1 |
| tekst pomocniczy / powierzchnia | `#4A5263` | `#F4F5F7` | 7.19:1 | 4.5:1 |
| link, primary / tło | `#0B4F9C` | `#FFFFFF` | 8.04:1 | 4.5:1 |
| tekst przycisku / primary | `#FFFFFF` | `#0B4F9C` | 8.04:1 | 4.5:1 |
| tekst przycisku / primary hover | `#FFFFFF` | `#083D79` | 10.75:1 | 4.5:1 |
| tekst przycisku secondary hover | `#0B4F9C` | `#E7F0FA` | 6.98:1 | 4.5:1 |
| tekst przycisku / danger | `#FFFFFF` | `#B3261E` | 6.54:1 | 4.5:1 |
| tekst przycisku / danger hover | `#FFFFFF` | `#8C1D17` | 9.12:1 | 4.5:1 |
| błąd / tło | `#B3261E` | `#FFFFFF` | 6.54:1 | 4.5:1 |
| błąd, confidence niski / tło błędu | `#B3261E` | `#FDECEA` | 5.72:1 | 4.5:1 |
| ostrzeżenie, confidence średni / tło | `#7A4A00` | `#FFF4E0` | 6.86:1 | 4.5:1 |
| sukces, confidence wysoki / tło | `#1E6B34` | `#E8F5EB` | 5.83:1 | 4.5:1 |
| info / tło info | `#0B4F9C` | `#E7F0FA` | 6.98:1 | 4.5:1 |
| tekst wyłączony / tło wyłączone | `#5F6673` | `#ECEEF1` | 4.97:1 | 4.5:1 |
| ramka pola / tło (UI) | `#767E8C` | `#FFFFFF` | 4.09:1 | 3:1 |
| ramka pola / powierzchnia (UI) | `#767E8C` | `#F4F5F7` | 3.75:1 | 3:1 |
| fokus / tło (UI) | `#0B4F9C` | `#FFFFFF` | 8.04:1 | 3:1 |
| fokus / powierzchnia (UI) | `#0B4F9C` | `#F4F5F7` | 7.37:1 | 3:1 |
| ramka błędu pola / tło (UI) | `#B3261E` | `#FFFFFF` | 6.54:1 | 3:1 |
| ramka badge wysoki / tło (UI) | `#2E7D45` | `#FFFFFF` | 5.08:1 | 3:1 |
| ramka badge średni / tło (UI) | `#A86500` | `#FFFFFF` | 4.64:1 | 3:1 |
| ramka badge niski / tło (UI) | `#B3261E` | `#FFFFFF` | 6.54:1 | 3:1 |

`--color-border` (`#D5D9E0`) celowo nie spełnia 3:1: służy tylko do linii dekoracyjnych, nigdy jako jedyna granica elementu interaktywnego. Zmiana dowolnego koloru wymaga ponownego policzenia tej tabeli.
