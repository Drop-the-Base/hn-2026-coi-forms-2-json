# System wizualny frontendu

Panel urzędnika, który poprawia wynik AI: wgrywa blankiet, czeka na wynik, sprawdza wskazane elementy i pobiera poprawiony JSON ([FR-E4](../docs/requirements.md), [FR-T1](../docs/requirements.md), [FR-T2](../docs/requirements.md)). Cel dostępności: WCAG 2.1 AA ([NFR-15](../docs/requirements.md)). Stack: shadcn/ui + Tailwind ([ADR-0011](../docs/adr/0011-frontend-react-vite.md)); tokeny to zmienne CSS, które Tailwind i shadcn czytają bez dodatkowych bibliotek.

Pliki obok:

| Plik | Co to |
|---|---|
| [design/tokens.css](design/tokens.css) | tokeny z §2–§5 jako CSS custom properties, 1:1 z tym dokumentem |
| [design/ui.css](design/ui.css) | komponenty bazowe z §6 na tokenach (wzorzec dla shadcn/Tailwind, nie kod produkcyjny) |
| [design/komponenty.html](design/komponenty.html) | arkusz komponentów we wszystkich stanach |
| [design/ekrany.md](design/ekrany.md) | makiety #47: logowanie, upload, lista zadań, postęp |
| [design/ekran-przegladu.md](design/ekran-przegladu.md) | makieta #48: przegląd wyniku |
| [design/kontrast.py](design/kontrast.py) | liczy kontrast par z §7 wzorem WCAG; po zmianie koloru uruchom go ponownie |
| [design/zrzuty/](design/zrzuty/) | zrzuty prototypów (headless Chrome, 1440 i 390 px) |

Prototypy HTML otwierasz wprost z dysku. Jedyna zależność sieciowa to font z Google Fonts; bez sieci działa fallback systemowy. Pasek „Makieta, stan:” w prawym dolnym rogu przełącza stany ekranu (pusty, błąd, utrata połączenia…) przez kotwicę w adresie i nie jest częścią produktu.

## 1. Kierunek: „Teczka sprawy”

Urzędnik nie tworzy formularza od zera, tylko sprawdza teczkę, którą przygotował ktoś inny, i zostawia uwagi na marginesie. Z tego bierzemy cztery rzeczy (i tylko te, reszta to standardowe kontrolki webowe):

- **Paleta.** Papier kancelaryjny (`paper`, ciepła szarość) jako tło, białe arkusze na nim, grzbiet teczki (`shell`, granat) jako pasek aplikacji, atrament (`accent`) jako jedyny akcent: główna akcja, zaznaczenie, fokus. Kolory stanów tylko tam, gdzie niosą znaczenie.
- **Typografia.** Jeden krój o wysokiej czytelności, bo urzędnik czyta identyfikatory, PESEL-e, numery działek i JSON: `Il1|`, `O0` i `rn/m` muszą się różnić.
- **Gęstość.** Średnia: tabele 14 px, kontrolki 40 px, arkusze bez cieni. Dużo pól na ekranie, ale z wyraźnym rytmem.
- **Sygnatura: margines pewności.** Obok każdego elementu poniżej progu stoi znacznik na marginesie, jak uwaga korektora: długość = wysokość elementu, wypełnienie = poziom pewności (pełny = niska, kreskowany = średnia, obrys = wysoka). Ten sam znacznik jest w rynnie edytora JSON, w marginesie podglądu formularza i w pierwszej kolumnie listy zadań. Urzędnik widzi „gdzie patrzeć” bez czytania liczb.

Dwie zasady z innych światów, które przyjęliśmy jako dyscyplinę:
- **Nawigacja jak na lotnisku:** pasek „Problem 3 z 7” jest zawsze widoczny i pokazuje tylko następną decyzję, z przyciskami Poprzedni / Następny (F8).
- **Akcja niszcząca osobno:** jedyna akcja tracąca pracę („Wyjdź bez pobierania”) ma osobny wariant z obrysem `error` i nigdy nie stoi jako przycisk wypełniony.

Odrzucone: gradienty, szkło, cienie jako ozdoba, ilustracje, zdjęcia, animacje wejścia, kolorowe lewe krawędzie kart, etykiety wersalikami. Tylko tryb jasny (praca w biurze, przy świetle dziennym).

Podgląd formularza (FR-E5) ma **własną, chłodną paletę `eu-*`** odwzorowaną z wizualizacji COI (`data/Materiały…/*wizualizacja*.docx`: niebiesko-szare tło, białe karty z zaokrągleniem, granatowe „Dalej”). Dzięki temu urzędnik od razu odróżnia „nasze narzędzie” od „tego, co zobaczy obywatel”.

## 2. Kolory

Wartości są w [design/tokens.css](design/tokens.css); poniżej rola każdego tokenu. Kontrast każdej pary: §7.

| Token | Hex | Użycie |
|---|---|---|
| `--color-paper` | `#F4F3EF` | tło strony, tło pola tylko do odczytu, hover wiersza i pola |
| `--color-paper-2` | `#EBEAE4` | tor paska postępu |
| `--color-sheet` | `#FFFFFF` | arkusze, pola, przyciski z obrysem |
| `--color-ink` | `#1A1D24` | tekst główny |
| `--color-muted` | `#565B66` | opisy, metadane, podpowiedzi, placeholder |
| `--color-rule` | `#D9D7CF` | linie dekoracyjne (podziały, ramki arkuszy); nigdy jedyna granica kontrolki |
| `--color-field-border` | `#767A84` | ramka pola i przycisku drugorzędnego (UI ≥ 3:1) |
| `--color-shell` | `#15213D` | pasek aplikacji |
| `--color-on-shell` / `-muted` | `#FFFFFF` / `#BCC5D8` | tekst na pasku |
| `--color-accent` | `#22408C` | przycisk główny, link, zaznaczenie, fokus |
| `--color-accent-hover` | `#1A3170` | hover przycisku głównego |
| `--color-accent-subtle` | `#E6EBF6` | hover przycisku drugorzędnego, zaznaczony wiersz, bieżący element |
| `--color-on-accent` | `#FFFFFF` | tekst na `accent` |
| `--color-focus` / `-on-shell` | `#22408C` / `#FFFFFF` | pierścień fokusu na jasnym tle / na pasku |
| `--color-backdrop` | `rgb(21 33 61 / 0.4)` | tło pod dialogiem |

Stany (tekst na tle stanu, znacznik na białym):

| Stan | Tekst | Tło | Znacznik / ramka |
|---|---|---|---|
| `error` (= pewność niska) | `#B42318` | `#FDEDEB` | `#B42318` |
| `warning` (= pewność średnia) | `#8A4B00` | `#FFF3DC` | `#B26A00` (`warning-mark`) |
| `success` (= pewność wysoka) | `#1E6B3A` | `#E7F3EB` | `#2F7D4A` (`success-mark`) |
| `info` | `accent` | `accent-subtle` | `accent` |

Edytor JSON: `code-key #22408C`, `code-string #17663A`, `code-number #9A4100`, `code-punct #565B66`, `code-line-no #6A6F79` na `code-gutter #F7F6F2`, bieżący element `code-current #EEF1F8`.

Podgląd eUsługi: `eu-ground #EEF2F7`, `eu-card #FFFFFF`, `eu-ink #1B1B1F`, `eu-label #33363D`, `eu-readonly #F3F5F8`, `eu-border #51596A`, `eu-primary #1A3E7A`. Używane wyłącznie wewnątrz ramki podglądu.

## 3. Typografia

**Atkinson Hyperlegible Next** (tekst) i **Atkinson Hyperlegible Mono** (edytor, identyfikatory), Braille Institute, licencja **SIL OFL 1.1**. Zaprojektowane pod czytelność dla osób słabowidzących: rozróżnialne `I l 1`, `0 O` (przekreślone zero), otwarte kształty; pełne polskie znaki (zakres latin-ext). Jeden krój na cały interfejs, dwie grubości.

> **Wejście fontu do kodu wymaga ADR-a** (nowa zależność, [ADR-0013](../docs/adr/0013-polityka-licencji.md)). Do tego czasu `--font-body` i `--font-mono` spadają na stos systemowy (`system-ui`, `ui-monospace`) i wszystko działa. W produkcji font self-hostujemy (pliki w repo, bez Google Fonts), żeby nie łamać NFR-03.

| Token | Rozmiar | Użycie |
|---|---|---|
| `--text-xs` | 0.8125rem (13 px) | badge, metadane, identyfikatory pod nazwą pliku |
| `--text-sm` | 0.875rem (14 px) | tabela, etykiety, przyciski, edytor, komunikaty |
| `--text-md` | 1rem (16 px) | tekst główny, pola formularza |
| `--text-lg` | 1.125rem (18 px) | nagłówek arkusza, sekcji w podglądzie |
| `--text-xl` | 1.3125rem (21 px) | tytuł formularza (przegląd, podgląd) |
| `--text-2xl` | 1.5rem (24 px) | tytuł strony |

- Skala stała w `rem` (powiększenie do 200%, WCAG 1.4.4), stosunek ok. 1,15. Bez płynnych nagłówków.
- Grubości: `--weight-regular` 400, `--weight-strong` 600. Nagłówki: jedna grubość, jeden kolor.
- `--leading-body` 1.5, `--leading-tight` 1.3. Liczby i godziny w tabelach: `font-variant-numeric: tabular-nums`.
- Etykiety, nagłówki tabel i zakładki: zdania, bez wersalików i rozstrzelenia.

## 4. Odstępy, wymiary

Krok 4 px: `--space-1` 4 px, `-2` 8, `-3` 12, `-4` 16, `-5` 20, `-6` 24, `-8` 32, `-12` 48. Typowo: ikona–tekst `1`, etykieta–pole `1`, odstęp pól `4`, padding arkusza `6`, odstęp arkuszy `6`.

`--control-h` 2.5rem (40 px; obszar kliknięcia 44 px przez `::before`), mały przycisk 2rem (obszar 44 px), `--shell-h` 3.5rem, `--container` 90rem, `--gutter` 2rem (1rem poniżej 60rem).

## 5. Promienie, cienie, ruch

| Token | Wartość | Użycie |
|---|---|---|
| `--radius-mark` | 2px | badge, znacznik marginesu, pasek postępu |
| `--radius-control` | 4px | przycisk, pole, komunikat |
| `--radius-sheet` | 6px | arkusz, dialog |
| `--radius-eu` | 8px | karta w podglądzie eUsługi (jak w wizualizacji COI) |
| `--shadow-raised` | `0 1px 2px rgb(21 33 61 / .08), 0 8px 24px -8px rgb(21 33 61 / .22)` | tylko dialog i pasek makiety |
| `--shadow-band` | linia `rule` + `0 4px 12px -6px …` | przyklejony pasek „Problem 3 z 7” |

Arkusze nie mają cienia: granicę wyznacza linia `rule`. Cień ma tylko to, co leży nad treścią.

Ruch tylko jako stan: `--dur-micro` 120 ms (hover, wciśnięcie), `--dur-short` 200 ms, `--ease-out`. Animujemy kolor tła, ramki i `transform`; nigdy `width`/`height`/`top`, nigdy `transition: all`. Przy `prefers-reduced-motion: reduce` wszystko staje (także spinner) i przewijanie do elementu jest natychmiastowe.

## 6. Komponenty bazowe

Wspólne: fokus to `outline: 2px solid var(--color-focus)` z odstępem 2 px, widoczny od razu (`:focus-visible`), na pasku aplikacji biały; w polach pierścień wewnętrzny (offset −3 px), żeby nie nachodził na sąsiada. Każda kontrolka ma `type`, etykietę i stany: spoczynek, hover (tylko `@media (hover: hover)`), fokus, wciśnięcie (1 px w dół), wyłączony, ładowanie, błąd. Ikony: jeden zestaw, kreska 2 px, 16 px, w kolorze tekstu, zawsze `aria-hidden` obok słowa (w prototypie maski SVG w `ui.css`; w kodzie biblioteka ikon wymaga ADR-a, kandydat: Lucide, ISC).

### Przycisk

40 px, padding `0 var(--space-4)`, `--radius-control`, `--text-sm` 600, ikona po lewej. Etykieta: czasownik + rzecz („Pobierz JSON”, „Wyślij 3 pliki”, „Przejrzyj wynik”).

| Wariant | Spoczynek | Hover | Kiedy |
|---|---|---|---|
| `primary` | tło `accent`, tekst `on-accent` | tło `accent-hover` | jedna główna akcja na ekranie (w dialogu: jedna w dialogu) |
| `secondary` | tło `sheet`, tekst `accent`, ramka `field-border` | tło `accent-subtle` | akcje poboczne, akcje w wierszu tabeli |
| `ghost` | bez tła i ramki, tekst `accent` | tło `accent-subtle` | akcje w nagłówku panelu („Formatuj”), „Usuń z listy” |
| `destructive` | tło `sheet`, tekst i ramka `error` | tło `error-bg` | akcja tracąca pracę; nigdy wypełniona, odsunięta od innych |

- Wyłączony: `disabled` + `opacity: 0.55` + `cursor: not-allowed`; obok zawsze tekst `muted` z powodem („Popraw 1 błąd schematu, aby pobrać.”). Kontrast elementów wyłączonych WCAG wyłącza z wymogu (1.4.3), powód jest w tekście obok.
- Ładowanie: spinner zamiast ikony, etykieta zmienia się na czynność („Wysyłanie”), szerokość nie skacze, `aria-busy="true"`.
- Mały wariant `btn--sm` (32 px) tylko w wierszach tabel i w pasku problemów.

### Pole formularza

Etykieta nad polem (`--text-sm` 600), pole 40 px, ramka 1 px `field-border` (grubość nigdy się nie zmienia), tło `sheet`, tekst 16 px. Pod polem jedna linia z zarezerwowaną wysokością (`min-height: 1lh`): podpowiedź (`muted`) albo komunikat błędu, który ją zastępuje.

| Stan | Wygląd |
|---|---|
| hover | tło `paper` |
| fokus | pierścień `focus` wewnątrz ramki |
| tylko do odczytu | tło `paper`, ramka bez zmian |
| wyłączony | `opacity: 0.55`, atrybut `disabled`, powód w podpowiedzi |
| błąd | ramka `error`, komunikat `error` z ikoną ✕: co poprawić („Ten token już nie działa. Wklej nowy.”), `aria-invalid="true"`, `aria-describedby` |

Wymagane: dopisek „(wymagane)” przy etykiecie. Placeholder pokazuje format, nigdy nie zastępuje etykiety. Wklejanie nigdy nie jest blokowane.

### Arkusz (karta)

Tło `sheet`, ramka 1 px `rule`, `--radius-sheet`, bez cienia. Nagłówek arkusza: `--text-lg` 600, padding `4 × 6`, linia `rule` pod spodem. Arkusz w arkuszu jest zakazany; podział wewnątrz robimy linią.

### Tabela

Pełna szerokość, `--text-sm`, bez zebry i bez ramki zewnętrznej. Nagłówki: zdania, 600, bez zawijania, dolna linia `field-border`. Wiersze: linia `rule`, hover `paper`. Liczby i godziny do prawej, `tabular-nums`. Pierwsza kolumna listy zadań to znacznik marginesu (§6, Pewność).

| Stan | Wygląd |
|---|---|
| zaznaczony | tło `accent-subtle`, `aria-selected="true"` |
| pusta | zamiast tabeli: co jest puste, dlaczego to ważne, jedna akcja (np. „Nie masz jeszcze zadań…”) |
| wąski ekran (< 48rem) | wiersz staje się blokiem z etykietami („Wgrano: 10:42”); kolumna z nazwą i akcja zawsze widoczne |

### Pewność (confidence, FR-T1): badge i znacznik marginesu

Trzy poziomy, każdy rozpoznawalny **bez koloru** na trzy sposoby: wzór, słowo, liczba.

| Poziom | Zakres (roboczy) | Wzór | Słowo | Kolory |
|---|---|---|---|---|
| wysoka | ≥ 0,85 | obrys | „Wysoka 0,93” | `success` |
| średnia | 0,60–0,84 | kreskowanie 135° | „Średnia 0,71” | `warning`, kreski `warning-mark` |
| niska | < 0,60 | pełne wypełnienie | „Niska 0,34” | `error` |

- **Badge:** `--text-xs` 600, tło `<stan>-bg`, tekst `<stan>`, po lewej próbka wzoru 10 × 14 px, potem słowo i wartość z przecinkiem dziesiętnym. Dla czytnika: ukryty prefiks „Pewność: ”, więc słychać „Pewność: niska 0,34”. Badge nie jest interaktywny.
- **Znacznik marginesu (sygnatura):** pasek 8 px szerokości, wysoki jak element obok, ten sam wzór. W edytorze: kolumna w rynnie przy liniach elementu. W podglądzie: margines 28 px po lewej stronie karty. Na liście zadań: pierwsza kolumna, poziom oceny ogólnej. Znacznik jest dekoracyjny (`aria-hidden`), informację niesie badge, lista problemów i nazwa dostępna.
- Progi są robocze; podświetlamy elementy poniżej `CONFIDENCE_REVIEW_THRESHOLD` (domyślnie 0,85), czyli średnie i niskie.

### Status zadania

Ikona + tekst, nigdy sam kolor: „W kolejce” (zegar, `muted`), „Analiza treści, krok 2 z 4” (spinner, `accent`), „Gotowe” (ptaszek w kole, `success`), „Błąd: plik zaszyfrowany hasłem” (✕ w kole, `error`, z przyczyną w kilku słowach).

### Komunikat

Tło `<stan>-bg`, ikona i tytuł w kolorze stanu, treść w `ink`, `--radius-control`. Bez kolorowej lewej krawędzi. Błąd mówi: co się stało, dlaczego i co zrobić („PDF jest zaszyfrowany hasłem. Zapisz go bez hasła… i wgraj ponownie.”), z jedną akcją. `role="alert"` dla błędów, `role="status"` dla reszty.

### Zakładki, postęp, dialog

- **Zakładki** (filtr listy, obszary przeglądu na wąskim ekranie): `role="tablist"`, aktywna z podkreśleniem 2 px `accent` i grubszą czcionką, licznik w nazwie. Rząd zakładek przewija się poziomo, nie zawija.
- **Pasek postępu:** natywny `<progress>` 8 px, tor `paper-2`, wartość `accent`, obok tekst „fragment 4 z 9” (nigdy sam pasek). Bez wartości: tylko spinner i tekst kroku.
- **Dialog:** natywny `<dialog>` (`showModal()`, fokus w środku, Esc zamyka), arkusz z `--shadow-raised`, tło `backdrop`. Ostateczność: tylko gdy alternatywą jest utrata pracy.

## 7. Kontrast (zmierzony)

Wzór WCAG 2.1 (luminancja względna), liczony skryptem [design/kontrast.py](design/kontrast.py) z wartości w `tokens.css`, nie na oko. Próg 4.5:1 dla tekstu, 3:1 dla elementów UI (ramki, fokus, znaczniki). Skrypt kończy się błędem, gdy któraś para nie spełnia progu.

| Para | Kolor | Tło | Wynik | Próg | |
|---|---|---|---|---|---|
| tekst / papier | `ink` #1A1D24 | `paper` #F4F3EF | 15.19:1 | 4.5:1 | spełnia |
| tekst / arkusz | `ink` #1A1D24 | `sheet` #FFFFFF | 16.87:1 | 4.5:1 | spełnia |
| tekst / hover wiersza | `ink` #1A1D24 | `paper-2` #EBEAE4 | 13.99:1 | 4.5:1 | spełnia |
| tekst pomocniczy / papier | `muted` #565B66 | `paper` #F4F3EF | 6.13:1 | 4.5:1 | spełnia |
| tekst pomocniczy / arkusz | `muted` #565B66 | `sheet` #FFFFFF | 6.81:1 | 4.5:1 | spełnia |
| tekst pomocniczy / hover wiersza | `muted` #565B66 | `paper-2` #EBEAE4 | 5.65:1 | 4.5:1 | spełnia |
| tekst paska aplikacji | `on-shell` #FFFFFF | `shell` #15213D | 15.95:1 | 4.5:1 | spełnia |
| tekst pomocniczy paska aplikacji | `on-shell-muted` #BCC5D8 | `shell` #15213D | 9.20:1 | 4.5:1 | spełnia |
| link, przycisk drugorzędny / arkusz | `accent` #22408C | `sheet` #FFFFFF | 9.63:1 | 4.5:1 | spełnia |
| link / papier | `accent` #22408C | `paper` #F4F3EF | 8.68:1 | 4.5:1 | spełnia |
| akcent / zaznaczenie, hover | `accent` #22408C | `accent-subtle` #E6EBF6 | 8.06:1 | 4.5:1 | spełnia |
| tekst przycisku głównego | `on-accent` #FFFFFF | `accent` #22408C | 9.63:1 | 4.5:1 | spełnia |
| tekst przycisku głównego, hover | `on-accent` #FFFFFF | `accent-hover` #1A3170 | 12.23:1 | 4.5:1 | spełnia |
| błąd / arkusz | `error` #B42318 | `sheet` #FFFFFF | 6.57:1 | 4.5:1 | spełnia |
| błąd, pewność niska / tło | `error` #B42318 | `error-bg` #FDEDEB | 5.79:1 | 4.5:1 | spełnia |
| ostrzeżenie, pewność średnia / tło | `warning` #8A4B00 | `warning-bg` #FFF3DC | 6.19:1 | 4.5:1 | spełnia |
| ostrzeżenie / arkusz | `warning` #8A4B00 | `sheet` #FFFFFF | 6.80:1 | 4.5:1 | spełnia |
| sukces, pewność wysoka / tło | `success` #1E6B3A | `success-bg` #E7F3EB | 5.72:1 | 4.5:1 | spełnia |
| sukces / arkusz | `success` #1E6B3A | `sheet` #FFFFFF | 6.52:1 | 4.5:1 | spełnia |
| edytor: klucz | `code-key` #22408C | `code-bg` #FFFFFF | 9.63:1 | 4.5:1 | spełnia |
| edytor: tekst | `code-string` #17663A | `code-bg` #FFFFFF | 7.00:1 | 4.5:1 | spełnia |
| edytor: liczba | `code-number` #9A4100 | `code-bg` #FFFFFF | 6.71:1 | 4.5:1 | spełnia |
| edytor: interpunkcja | `code-punct` #565B66 | `code-bg` #FFFFFF | 6.81:1 | 4.5:1 | spełnia |
| edytor: klucz w bieżącym elemencie | `code-key` #22408C | `code-current` #EEF1F8 | 8.52:1 | 4.5:1 | spełnia |
| edytor: tekst w bieżącym elemencie | `code-string` #17663A | `code-current` #EEF1F8 | 6.19:1 | 4.5:1 | spełnia |
| edytor: numer linii | `code-line-no` #6A6F79 | `code-gutter` #F7F6F2 | 4.67:1 | 4.5:1 | spełnia |
| podgląd: tekst / karta | `eu-ink` #1B1B1F | `eu-card` #FFFFFF | 17.17:1 | 4.5:1 | spełnia |
| podgląd: etykieta / karta | `eu-label` #33363D | `eu-card` #FFFFFF | 12.10:1 | 4.5:1 | spełnia |
| podgląd: pole tylko do odczytu | `eu-ink` #1B1B1F | `eu-readonly` #F3F5F8 | 15.72:1 | 4.5:1 | spełnia |
| podgląd: tytuł / tło | `eu-ink` #1B1B1F | `eu-ground` #EEF2F7 | 15.27:1 | 4.5:1 | spełnia |
| podgląd: przycisk „Dalej” | `sheet` #FFFFFF | `eu-primary` #1A3E7A | 10.43:1 | 4.5:1 | spełnia |
| ramka pola / arkusz | `field-border` #767A84 | `sheet` #FFFFFF | 4.30:1 | 3.0:1 | spełnia |
| ramka pola / papier | `field-border` #767A84 | `paper` #F4F3EF | 3.87:1 | 3.0:1 | spełnia |
| fokus / arkusz | `focus` #22408C | `sheet` #FFFFFF | 9.63:1 | 3.0:1 | spełnia |
| fokus / papier | `focus` #22408C | `paper` #F4F3EF | 8.68:1 | 3.0:1 | spełnia |
| fokus / zaznaczony wiersz | `focus` #22408C | `accent-subtle` #E6EBF6 | 8.06:1 | 3.0:1 | spełnia |
| fokus / pasek aplikacji | `focus-on-shell` #FFFFFF | `shell` #15213D | 15.95:1 | 3.0:1 | spełnia |
| ramka pola z błędem, znacznik niski / arkusz | `error` #B42318 | `sheet` #FFFFFF | 6.57:1 | 3.0:1 | spełnia |
| kreskowanie znacznika średniego / arkusz | `conf-medium-mark` #B26A00 | `sheet` #FFFFFF | 4.24:1 | 3.0:1 | spełnia |
| obrys znacznika wysokiego / arkusz | `conf-high-mark` #2F7D4A | `sheet` #FFFFFF | 5.06:1 | 3.0:1 | spełnia |
| podgląd: ramka pola | `eu-border` #51596A | `eu-card` #FFFFFF | 7.03:1 | 3.0:1 | spełnia |
| zaznaczenie elementu w podglądzie | `accent` #22408C | `eu-card` #FFFFFF | 9.63:1 | 3.0:1 | spełnia |

`--color-rule` (`#D9D7CF`) celowo nie spełnia 3:1: to linia dekoracyjna, nigdy jedyna granica kontrolki. `--color-backdrop` i elementy wyłączone nie są mierzone (WCAG ich nie wymaga).

## 8. Dostępność w skrócie (NFR-15)

- Stan nigdy nie jest tylko kolorem: słowo + ikona, a dla pewności także wzór.
- Fokus widoczny zawsze, kolejność tabulacji zgodna z kolejnością na ekranie, skip link jako pierwszy element strony.
- Zmiany (krok pipeline'u, przejście do problemu, liczba błędów schematu) ogłaszamy w regionie `aria-live="polite"`; błędy blokujące w `role="alert"`.
- Obszar kliknięcia ≥ 44 px, tekst ≥ 13 px (ciągły ≥ 14 px), powiększenie do 200% bez utraty treści, brak poziomego przewijania strony przy 320 px (tabele i edytor przewijają się w swoim kontenerze).
- Nagłówki bez przeskoków; w podglądzie formularza strona to `h3`, sekcja `h4`.
