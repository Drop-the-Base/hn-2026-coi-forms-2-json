# Wymagania

Źródła: [treść zadania](COI%20-%20Pełna%20treść%20zadania%20konkursowego.pdf) (sekcje 3–8), [materiały dla uczestników](../data/Materiały%20do%20zadania%20dla%20Uczestników/), [analiza danych](analiza-i-charakterystyka-danych.md).

Oznaczenia:
- **Źródło**: `Z` = treść zadania (np. `Z 5` = sekcja 5), `R` = Reguły techniczne konfiguracji, `S` = Standardy projektowania formularzy, `DI` = Dane inicjalne, `SŁ` = Słowniki, `T` = decyzja zespołu.
- **Priorytet**: `MUST` = obowiązkowe do oceny, `EXT` = rozszerzenie punktowane, `TEAM` = nasze, poprawia ocenę (intuicyjność, jakość, potencjał wdrożeniowy).

## 1. Wymagania funkcjonalne

### 1.1 Zakres obowiązkowy

| ID | Wymaganie | Źródło | Priorytet |
|---|---|---|---|
| FR-01 | REST API przyjmuje **pojedynczy plik** z blankietem formularza. | Z 3.2.I, Z 5 | MUST |
| FR-02 | Obsługiwane formaty: `.pdf`, `.doc`, `.docx`, `.ods`, `.xlsx`, `.jpg`, `.jpeg`, `.png`. Rozszerzenia bez rozróżniania wielkości liter (dane zawierają `.PDF`, `.JPG`). | Z 5 | MUST |
| FR-03 | Akceptujemy tylko obsługiwane formaty. Typ MIME wykryty z **zawartości** musi pasować do rozszerzenia. Uwaga: w danych są pliki `.DOC`, które są w środku DOCX. | Z 5 | MUST |
| FR-04 | Nazwa pliku ma ≤ 250 znaków i nie zawiera `; : > < / \ \| ' * % $`. | Z 5 | MUST |
| FR-05 | Maksymalny rozmiar pliku jest konfigurowalny parametrem aplikacji. | Z 5 | MUST |
| FR-06 | Odpowiedź to JSON konfiguracji formularza **w strukturze wzorców** (`title`, `tabs`, `flow`) i zgodny z `importowanyPlikJsonSchemat.json`. Gdy schemat i wzorce się różnią, wygrywają wzorce (patrz sekcja 3). | Z 3.2.I, Z 5 | MUST |
| FR-07 | JSON oddaje treść importowanego formularza: dane, które trzeba podać, i informacje o procesie. | Z 3.2.I | MUST |
| FR-08 | JSON spełnia reguły techniczne: ≥ 2 strony, ostatnia `FINISH`, pozostałe `MAIN`, każda strona ma ≥ 1 pole, każde pole leży w sekcji, nie ma sekcji w sekcji, na `FINISH` nie ma pól do wpisywania, każde pole ma atrybut obligatoryjności, strony są połączone w `flow`, pola zależne od innych mają `states` (JSONata), tytuł ma ≤ 255 znaków. | R | MUST |
| FR-09 | JSON spełnia Standardy projektowania: tematyczne strony i sekcje, kolejność (strony postępowania → sprawa → kontakt i zgody → podsumowanie), sekcje predefiniowane, typ pola dopasowany do danych, zgody w `CONSENT_SECTION`. | S, Z 3.2.I | MUST |
| FR-10 | API jest chronione uwierzytelnianiem JWT. Parametry JWT są konfigurowalne. | Z 5 (Konfiguracja aplikacji) | MUST |

### 1.2 Rozszerzenia punktowane

| ID | Wymaganie | Źródło | Priorytet |
|---|---|---|---|
| FR-E1 | Pola są powiązane ze słownikami (`dictionaryName`) i danymi inicjalnymi (`defaultValue` + `defaultValueType: EXTERNAL_SYSTEM`, `readOnly`). | Z 3.3.I, SŁ, DI | EXT |
| FR-E2 | Propozycja nowego słownika: nazwa, struktura, zastosowanie. Kandydaci są w [analizie](analiza-i-charakterystyka-danych.md#64-rozszerzenia-punktowane-i-ich-pokrycie-przez-dane). | Z 3.3.II, SŁ | EXT |
| FR-E3 | Zależności między polami, sekcjami i stronami: stany `SHOW` / `READ_ONLY` oraz przepływy zależne od wyboru użytkownika. | Z 3.3.III, R | EXT |
| FR-E4 | Frontend: wgrywanie plików i przeglądanie wynikowego JSON-a. | Z 3.3.IV | EXT |
| FR-E5 | Wizualizacja: render formularza eUsługi z wynikowego JSON-a. | Z 3.3.V | EXT |
| FR-E6 | Walidacje pól (typ, długość, telefon, PESEL, NIP…) i ułatwienia UX: przetwarzanie wsadowe (batch), makiety. | Z 3.3.VI | EXT |

### 1.3 Wymagania zespołu

| ID | Wymaganie | Uzasadnienie | Priorytet |
|---|---|---|---|
| FR-T1 | Każdy element wyniku ma **confidence score** (0–1). Wynik ma też ocenę ogólną i listę problemów (naruszone reguły, niepewne pola). | Urzędnik wie, co sprawdzić. Intuicyjność to 20% oceny. | TEAM |
| FR-T2 | Panel we frontendzie pozwala poprawić JSON (edytor + podgląd formularza) i pobrać poprawioną wersję. | Docelowy użytkownik to urzędnik, który poprawia wynik AI. | TEAM |
| FR-T3 | Tryb asynchroniczny: `POST /jobs` → `202` + `job_id`, `GET /jobs/{id}` → status / wynik. Tryb synchroniczny z FR-01 zostaje. | Długie przetwarzanie (OCR, LLM), batch z FR-E6. | TEAM |
| FR-T5 | Postęp przetwarzania na żywo (SSE): frontend pokazuje bieżący krok pipeline'u, postęp (np. OCR strony 3/16) i ostrzeżenia. | Intuicyjność, długie przetwarzanie. [ADR-0014](adr/0014-sse-postep-pipeline.md) | TEAM |
| FR-T4 | Zbiór ewaluacyjny: wzorce + ręcznie przygotowane złote JSON-y dla pozostałych formularzy. Runner ewaluacji liczy metryki jakości. | Mamy tylko 2 wzorce. Bez evali nie wiemy, czy zmiana poprawia wynik. | TEAM |

## 2. Wymagania niefunkcjonalne

| ID | Wymaganie | Źródło | Priorytet |
|---|---|---|---|
| NFR-01 | Język backendu: Python 3.14+ (alternatywa w zadaniu: Java 21+). | Z 5 | MUST |
| NFR-02 | Tylko biblioteki i narzędzia open source, **bez copyleftu** (np. AGPL, GPL). Polityka licencji: [ADR-0013](adr/0013-polityka-licencji.md). | Z 5 | MUST |
| NFR-03 | Bez zewnętrznych API, MCP i SaaS w działającym rozwiązaniu. **Bez LLM dostępnych tylko przez API.** Modele działają lokalnie. | Z 5 | MUST |
| NFR-04 | Bez licencji komercyjnych. Funkcje „enterprise" narzędzi open-core są zakazane. | Z 5 | MUST |
| NFR-05 | Najnowsze stabilne wersje bibliotek i frameworków, przypięte w lockfile. | Z 5 | MUST |
| NFR-06 | Plik jest przetwarzany **wyłącznie tymczasowo**: w pamięci albo w przestrzeni tymczasowej na czas realizacji żądania. Brak trwałego zapisu. | Z 5 | MUST |
| NFR-07 | Docker: kompletna konfiguracja, oficjalne obrazy bazowe, lekkie dystrybucje (preferowany Alpine), jawne wersje (bez `latest`), proces na użytkowniku bez uprawnień roota, tylko niezbędne porty, sekrety tylko w runtime (zmienne środowiskowe). | Z 5 | MUST |
| NFR-08 | Konfiguracja runtime: maks. rozmiar pliku, JWT, parametry integracji (np. adres modelu). | Z 5 | MUST |
| NFR-09 | `README.md`: budowanie obrazu, uruchomienie, konfiguracja, opis REST API. | Z 5 | MUST |
| NFR-10 | Dokumentacja architektury: [architecture.md](architecture.md) + [ADR](adr/README.md). | Z 3.2.II | MUST |
| NFR-11 | Rozwiązanie generalizuje: na obronie dostanie **nowe, nieznane pliki**. Nie hardkodujemy znanych formularzy. | Z 6 | MUST |
| NFR-12 | Jakość kodu (20% oceny): zasady w [coding-rules.md](coding-rules.md). | Z 8 | MUST |
| NFR-13 | Potencjał wdrożeniowy, w tym koszt (20% oceny): małe modele lokalne, możliwość działania bez GPU, mierzony koszt i czas żądania. | Z 8 | MUST |
| NFR-14 | Obserwowalność: tracing każdego żądania przez wszystkie usługi, metryki latencji, liczby żądań, błędów, tokenów i kosztu na żądanie. | T | TEAM |
| NFR-15 | Dostępność: generowane formularze i nasz frontend celują w WCAG 2.1 AA. | S (Ogólne zasady) | TEAM |
| NFR-16 | Wymiana dostawców (model, OCR, broker) przez zmianę adaptera i konfiguracji, bez zmian w domenie. | T | TEAM |

## 3. Konflikty i niejasności w wymaganiach

Każdy konflikt ma decyzję roboczą. Zmieniamy ją po odpowiedzi mentorów COI.

| # | Konflikt | Decyzja robocza | Gdzie opisane |
|---|---|---|---|
| K-01 | Kolejka asynchroniczna kontra „w odpowiedzi aplikacja zwraca dokument JSON" (FR-01, FR-06). | Dwa tryby: synchroniczny endpoint czeka na wynik z limitem czasu, asynchroniczny `/jobs` służy frontendowi i batchowi. | [ADR-0004](adr/0004-przetwarzanie-asynchroniczne-rabbitmq.md) |
| K-02 | Plik musi przejść z API do workera, a NFR-06 pozwala tylko na przestrzeń tymczasową na czas żądania. | Współdzielony wolumen `tmpfs` (RAM). Plik usuwany po zadaniu i po TTL. Wiadomości w brokerze nie są trwałe. | [ADR-0005](adr/0005-pliki-tymczasowe-tmpfs.md) |
| K-03 | Grafana (a także Tempo i Loki) ma licencję **AGPL**, a NFR-02 zabrania copyleftu. | Grafana tylko w opcjonalnym profilu `observability`, nie jest zależnością aplikacji. Zamiennik bez copyleftu: Perses. Pytanie do mentorów. | [ADR-0009](adr/0009-obserwowalnosc-opentelemetry.md) |
| K-04 | Preferowany Alpine kontra biblioteki ML/OCR (musl, brak gotowych wheeli). | Obraz `python:3.14-slim` dla workera. Alpine tam, gdzie się da (frontend, API, jeśli zależności pozwolą). | [ADR-0012](adr/0012-obraz-bazowy-slim.md) |
| K-05 | Wzorce mają puste `validation`, a reguły wymagają atrybutu obligatoryjności. | Wpisujemy `["REQUIRED", …]` jako tablicę stringów, zgodnie z opisem pliku JSON. | [analiza §5](analiza-i-charakterystyka-danych.md#5-niespójności-wzorce-vs-dokumentacja) |
| K-06 | Nazwy słowników we wzorcach (`TERYT_4G_DOWODOWY`, `Kraje`) są inne niż w dokumencie Słowniki. | Używamy nazw ze wzorców. | analiza §5 |
| K-07 | Strona `FINISH`: reguły pozwalają tylko na `INFO_SECTION`, wzorce mają `SECTION` + `TEXT_BLOCK`. | Idziemy za wzorcami. | analiza §5 |
| K-08 | Bramka LLM z „wyłączaniem LLM" i kosztami kontra NFR-03/04 (open-core, funkcje enterprise). | Bramka tylko z funkcjami z licencji open source. | [ADR-0008](adr/0008-bramka-llm.md) |

## 4. Rezultaty do oddania

| Element | Źródło |
|---|---|
| Opis i tytuł projektu | Z 4 |
| Prezentacja PDF, maks. 10 slajdów | Z 4 |
| Wynikowe pliki JSON dla formularzy 2, 3, 4, 6, 7, 8, 9 | Z 4, Z 3.1.II |
| Film ≤ 3 min w otwartym repozytorium (link) | Z 4 |
| Repozytorium kodu | Z 4 |
| Opcjonalnie: zrzuty ekranu, link do demo, grafiki | Z 4 |

## 5. Kryteria oceny (do priorytetyzacji)

| Kryterium | Waga | Co z tego wynika dla nas |
|---|---|---|
| Kompletność (minimum + rozszerzenia I–V) | 30% | Najpierw MUST, potem EXT w kolejności: E3 (zależności) → E1 (słowniki) → E4 (frontend) → E6 (walidacje) → E2 (nowy słownik) |
| Intuicyjność | 20% | Frontend z confidence score i edycją (FR-T1, FR-T2) |
| Jakość kodu | 20% | [coding-rules.md](coding-rules.md) |
| Potencjał wdrożeniowy i koszt | 20% | Małe modele lokalne, metryki kosztu (NFR-13, NFR-14) |
| Oryginalność | 10% | Pipeline szablony + AI, confidence score, eval loop |
