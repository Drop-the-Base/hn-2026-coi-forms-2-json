# Ekrany: logowanie, upload, lista zadań, postęp

Ścieżka „wgraj plik → czekaj na wynik” (issue #47). Wymagania: [FR-E4](../../docs/requirements.md) (upload i przegląd), [FR-E6](../../docs/requirements.md) (batch), [FR-T3](../../docs/requirements.md) (`POST /jobs` → `job_id`), [FR-T5](../../docs/requirements.md) (postęp SSE, [ADR-0014](../../docs/adr/0014-sse-postep-pipeline.md)), [FR-02..05](../../docs/requirements.md) (walidacja pliku), [FR-10](../../docs/requirements.md) (JWT), [NFR-06](../../docs/requirements.md) (pliki i wyniki tylko tymczasowo), [NFR-15](../../docs/requirements.md). Wygląd: tokeny i komponenty z [DESIGN.md](../DESIGN.md).

Prototypy otwierasz w przeglądarce; stany przełącza pasek „Makieta, stan:” w prawym dolnym rogu. Zrzuty: [zrzuty/](zrzuty/).

Powłoka wspólna dla wszystkich ekranów po zalogowaniu: granatowy pasek z nazwą narzędzia, jedną pozycją nawigacji „Zadania” (sidebar niepotrzebny przy jednym celu), czasem ważności sesji z JWT i „Wyloguj”. Poniżej 60rem znika opis przy nazwie i czas sesji.

## 1. Logowanie: [logowanie.html](logowanie.html)

| Stan | Zrzut |
|---|---|
| domyślny | [logowanie.png](zrzuty/logowanie.png) |
| token wygasł | [logowanie-blad.png](zrzuty/logowanie-blad.png) |

- Jedno pole „Token dostępu” (JWT od administratora, FR-10), maskowane, z przełącznikiem „Pokaż” (`aria-pressed`). Pole przyjmuje wklejenie; spacje i znaki nowej linii na końcach obcinamy.
- „Zaloguj” jest aktywne zawsze; walidacja po wysłaniu. Przed wysłaniem sprawdzamy lokalnie tylko format (trzy części rozdzielone kropką) i datę `exp`; podpis sprawdza API przy pierwszym żądaniu.
- Błędy (komunikat nad formularzem + ramka pola + linia pod polem, fokus wraca do pola):
  - wygasły token: „Token wygasł 21.11.2026 o 9:12. Poproś administratora o nowy token…”;
  - zły format: „To nie wygląda na token. Token ma trzy części rozdzielone kropkami i zaczyna się od „eyJ”.”;
  - API odrzuca (401): „Serwer nie przyjął tokenu. Sprawdź, czy wkleiłeś go w całości.”
- Token trzymamy w `sessionStorage` (znika po zamknięciu karty), nigdy w adresie URL. Wygaśnięcie w trakcie pracy: przy 401 wracamy tu z tym samym komunikatem, a otwarty edytor z niepobranymi poprawkami najpierw pokazuje dialog z ekranu przeglądu (żeby nie stracić pracy).
- Pod formularzem jedno zdanie o tymczasowym przetwarzaniu plików (NFR-06), bo to pierwsze pytanie urzędnika.

## 2. Upload i lista zadań: [zadania.html](zadania.html)

| Stan | Zrzut |
|---|---|
| lista | [zadania.png](zrzuty/zadania.png) |
| wybrano 5 plików, 2 z błędami | [zadania-wsad.png](zrzuty/zadania-wsad.png), wąsko: [zadania-390.png](zrzuty/zadania-390.png) |
| pierwsze wejście, brak zadań | [zadania-pusto.png](zrzuty/zadania-pusto.png) |

Jeden ekran, dwa arkusze: „Wgraj formularze” nad „Twoje zadania”. Urzędnik wraca tu po każdym wyniku, więc upload jest zawsze pod ręką, bez osobnej strony.

### Wgrywanie (pojedyncze i wsadowe, FR-E6)

- Strefa upuszczania + przycisk „Wybierz pliki” (`<input type="file" multiple accept=…>` z etykietą). Upuszczenie na całą stronę też działa; strefa podświetla się tłem `accent-subtle` i ramką `accent`.
- Pod tekstem strefy zawsze widoczne zasady: obsługiwane formaty (FR-02) i limit rozmiaru z konfiguracji API (FR-05, w makiecie 20 MB).
- Po wybraniu plików pojawia się tabela „Wybrane pliki (N)”. Każdy plik jest sprawdzany w przeglądarce **od razu**, przed wysłaniem:
  - rozszerzenie z listy FR-02, bez rozróżniania wielkości liter (`.DOC`, `.JPG` przechodzą);
  - nazwa ≤ 250 znaków, bez `; : > < / \ | ' * % $` (FR-04): komunikat wskazuje znak („Nazwa zawiera niedozwolony znak „:”.”);
  - rozmiar ≤ limit (FR-05): komunikat podaje obie liczby i radę („Plik ma 34,2 MB, limit to 20 MB. Zmniejsz rozdzielczość skanu.”).
  Kilka błędów jednego pliku łączymy w jednej komórce. Zgodność MIME z zawartością (FR-03) sprawdza dopiero API; odrzucenie wraca jako zadanie ze stanem „Błąd” i przyczyną.
- „Wyślij 3 pliki” (główny przycisk) wysyła tylko poprawne; obok tekst, ile pominie i dlaczego. Gdy żaden plik nie jest poprawny, przycisk jest wyłączony z powodem obok. Każdy plik to osobne `POST /api/v1/jobs` (FR-T3); w trakcie przycisk pokazuje „Wysyłanie 2 z 3”, a wysłane pliki od razu znikają z tabeli i pojawiają się na liście zadań.
- „Usuń z listy” (tekstowy, nie niszczący: plik jest dalej na dysku urzędnika).

### Lista zadań

- Kolumny: znacznik pewności (sygnatura z DESIGN.md), plik (nazwa jako link + krótki `job_id` mono), godzina wgrania, stan, ocena ogólna (badge), liczba problemów, akcja.
- Akcja zależy od stanu: „Pokaż postęp” (w kolejce, w toku), „Przejrzyj wynik” (gotowe; wypełniony tylko w najnowszym wierszu do przeglądu, żeby na ekranie był jeden główny przycisk), „Szczegóły błędu”.
- Pod „Gotowe” czas wygaśnięcia wyniku („wynik dostępny do 11:34”): API trzyma wynik w pamięci z TTL (NFR-06), więc urzędnik musi wiedzieć, ile ma czasu. 10 minut przed końcem tekst zmienia kolor na `warning` i dostaje ikonę.
- Filtry jako zakładki z licznikami: Wszystkie, W toku, Do przeglądu, Błędy. Filtr jest w adresie (`?stan=w-toku`), więc przetrwa odświeżenie.
- Stan wierszy w toku odświeża się z SSE otwartego zadania albo pollingiem `GET /jobs/{id}` co 5 s; zmiana stanu jest ogłaszana w `aria-live="polite"` („Wniosek o wynajęcie świetlicy: gotowe, 7 problemów.”).
- Ładowanie listy: szkielet trzech wierszy w kształcie tabeli, nie spinner. Błąd pobrania listy: komunikat `error` w arkuszu z „Spróbuj ponownie”.
- Pusto: „Nie masz jeszcze zadań” + jedno zdanie, co się stanie po wgraniu. Akcją jest strefa uploadu nad listą, bez drugiego przycisku.
- Lista żyje w pamięci przeglądarki na czas sesji. Serwer nie ma endpointu listy (wymyślanie go byłoby YAGNI); po zamknięciu karty lista znika, tak jak wyniki po TTL.
- Wąsko (< 48rem): wiersz staje się blokiem z etykietami („Wgrano: 10:42”), znacznik pewności zostaje jako pasek po lewej.

## 3. Postęp na żywo (FR-T5): [postep.html](postep.html)

| Stan | Zrzut |
|---|---|
| w toku, z ostrzeżeniami | [postep.png](zrzuty/postep.png), wąsko: [postep-390.png](zrzuty/postep-390.png) |
| gotowe | [postep-gotowe.png](zrzuty/postep-gotowe.png) |
| błąd przetwarzania | [postep-blad.png](zrzuty/postep-blad.png) |
| utrata połączenia SSE | [postep-utrata-polaczenia.png](zrzuty/postep-utrata-polaczenia.png) |

- Nagłówek: nazwa pliku, `job_id`, godzina, rozmiar; po prawej „Na żywo, trwa 1 min 12 s”.
- „Przebieg” to rejestr czterech kroków pipeline'u (architecture.md §4) jedną listą `<ol>`: Odczyt pliku, Analiza treści przez model, Budowa formularza, Sprawdzenie reguł. Każdy krok: godzina rozpoczęcia (mono, kolumna po lewej jak w dzienniku), kropka stanu (oczekuje: pusta; w toku: spinner; zakończony: ptaszek na `success`; błąd: ✕ na `error`), tytuł i `message` ze zdarzenia SSE.
- Gdy zdarzenie ma `progress`, pod krokiem pasek postępu z tekstem („fragment 4 z 9”, „OCR strony 3 z 16”). Bez `progress`: tylko spinner i tekst.
- „Ostrzeżenia (N)” w osobnym arkuszu obok: każde z treścią, krokiem i godziną. Ostrzeżenia nie przerywają pracy, a po zakończeniu trafiają też do listy problemów w przeglądzie.
- `aria-live="polite"` ogłasza tylko zmianę kroku i koniec („Analiza treści przez model: zakończona.”), nie każdy tik postępu.
- Gotowe: nad rejestrem arkusz „Wynik gotowy” z oceną ogólną, liczbą błędów i elementów do sprawdzenia oraz głównym „Przejrzyj wynik”. Nie przekierowujemy automatycznie (urzędnik może być w innym miejscu strony); fokus przenosimy na nagłówek „Wynik gotowy” tylko, jeśli był na stronie postępu.
- Błąd: komunikat `error` z przyczyną z `message` i radą, krok z ✕, kolejne „czeka”, akcja „Wgraj inny plik”. Plik jest już usunięty z serwera i to piszemy wprost.
- Utrata SSE: komunikat `warning` „Utracono połączenie na żywo. Przetwarzanie trwa dalej. Sprawdzamy stan co 5 sekund…”, przełączenie na polling `GET /jobs/{id}` (ADR-0014), próba ponownego połączenia SSE w tle. Po powrocie komunikat znika.
- Brak akcji „Anuluj”: API jej nie ma. Wyjście z ekranu nie przerywa zadania, co mówi link „Zadania”.

## Poza zakresem

Panel administratora i wydawanie tokenów, historia zadań między sesjami, anulowanie zadania, powiadomienia systemowe przeglądarki. Do osobnych issue, gdy backend je umożliwi.
