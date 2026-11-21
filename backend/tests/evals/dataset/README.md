# Zbiór ewaluacyjny (FR-T4, ADR-0010)

`golden/<nr formularza>.json` to złoty JSON, przygotowany ręcznie według Standardów i reguł technicznych. Runner (`tests/evals/test_evals.py`) paruje go z predykcją o tej samej nazwie pliku. `tests/unit/test_golden.py` sprawdza każdy plik z `golden/`: reguły bez ERROR, brak odwołań w `states` do nieistniejących pól i stron, oficjalny schemat.

## 2, 3, 4: wspólne

Pliki generują `golden/build_golden_<nr>.py` ze wspólnymi krokami w `golden/_common.py` (szkic `FormDraft` → `compose` → ręczne poprawki: tytuły stron, techName, opisy, położenie sekcji). Uruchom z `backend/`: `uv run python -m tests.evals.dataset.golden.build_golden_2` (przez `-m`, bo skrypty importują `_common`). Identyfikatory są losowe, więc każde uruchomienie zmienia cały plik.

Wspólne decyzje (Standardy, K-05..K-14): strony Dane → sprawa → Kontakt i zgody → Strona końcowa; usuwamy podpis, datę, „wypełnij wielkimi literami”, podstawę prawną i pouczenia; dane wnioskodawcy z papieru zastępują bloki predefiniowane; zgoda RODO z linkiem do klauzuli jest zawsze.

## 2. Wniosek o zwrot opłaty skarbowej (Stawiguda)

4 strony, 18 sekcji, 58 pól, 31 stanów SHOW.

- **Kto składa**: papier ma „Nazwa / Imię i nazwisko” i NIP oraz dane pełnomocnika, więc wszystkie trzy opcje: Swoim, Innej osoby, Osoby prawnej (Standardy: dane osoby i firmy → wszystkie możliwości).
- **Dane pełnomocnika (2.4)** i **załączniki (7)**: pełnomocnictwo i dowód opłaty za nie to bloki Pełnomocnictwo i Opłata skarbowa v1/v2. Nie dublujemy ich w sekcji Załączniki.
- **Dane kontaktowe (2.3)** → blok Dane do kontaktu (opcjonalne, jak na papierze).
- **Wysokość opłaty** → NUMBER „Kwota opłaty” (jak „Kwota” we wzorcu 5).
- **Sposób zwrotu**: RADIO; „w kasie organu” zmienione na „w kasie urzędu” (prostszy język). Przy przelewie widać „Numer rachunku” i „Imię i nazwisko lub nazwa właściciela rachunku” (`wlasciciel_rachunku`). Papier ma tylko „Dane właściciela”; adresu właściciela nie zbieramy, do przelewu wystarczy nazwa.
- **Uzasadnienie**: TEXTAREA, wskazówka z papieru jako opis pola.

## 3. Wniosek o wydanie zaświadczenia (Młynary)

4 strony, 14 sekcji, 39 pól, 19 stanów SHOW.

- **Kto składa**: papier zbiera tylko dane osoby (imię, nazwisko, adres, PESEL), więc Swoim albo Innej osoby. Telefon → Dane do kontaktu.
- **Rodzaj zaświadczenia**: „Proszę o wydanie zaświadczenia o:*” bez „niepotrzebne skreślić” → CHECKBOX (można zaznaczyć kilka). Opcje przepisane w mianowniku. „Inne” pokazuje TEXTAREA `inny_rodzaj_zaswiadczenia`.
- **Cel**: „celem przedłożenia w …” → TEXT_FIELD „Gdzie przedstawisz zaświadczenie” (`cel_wydania`).
- **Opłata 17 zł**: sekcja „Opłata skarbowa” na stronie Kontakt i zgody (Standardy: opłaty na przedostatniej stronie, `compose` kładzie je na stronie sprawy), TEXT_BLOCK z kwotą i kontem z papieru + wymagany plik z potwierdzeniem przelewu.
- **Niejasne, pominięte**: opłata jest „od każdego egzemplarza”, ale papier nie pyta o liczbę egzemplarzy, więc nie dodajemy pola. Zwolnień z opłaty (art. 2 i 7) nie modelujemy, więc plik z potwierdzeniem jest zawsze wymagany.

## 4. Wniosek o wynajęcie lub użyczenie świetlicy wiejskiej (Płoskinia)

4 strony, 14 sekcji, 44 pola, 21 stanów SHOW.

- **Tytuł**: „wynajęcie/użyczenie*” → „Wniosek o wynajęcie lub użyczenie świetlicy wiejskiej”.
- **Adresat**: „Wójt Gminy Płoskinia” → sekcja „Organ, do którego jest składany wniosek”.
- **Kto składa**: tylko dane osoby → Swoim albo Innej osoby.
- **Wynajem / użyczenie**: „*” na papierze → RADIO „Wybierz, czego dotyczy wniosek”.
- **Miejscowość świetlicy**: TEXT_FIELD; nie znamy listy świetlic gminy, więc nie SELECT.
- **Termin od–do** → dwa DATEPICKER-y. **Cel** → TEXT_FIELD z przykładami z papieru w opisie. **Liczba uczestników** → NUMBER.
- **Osoba odpowiedzialna**: RADIO „Ja / Inna osoba”; przy „Inna osoba” widać imię, nazwisko (`*_osoba_odpowiedzialna`) i plik ze zgodą i oświadczeniem tej osoby (papier każe je załączyć). Wymóg pełnoletności jest w opisie sekcji.
- **Oświadczenia (pkt 4)**: 4 wymagane zgody w CONSENT_SECTION „Zgody i oświadczenia”, w czasie teraźniejszym, bez form rodzajowych („zapoznałem/am się” → „Znam warunki…”), plus zgoda RODO.
- **Pominięte**: opłaty za wynajem papier nie podaje (jest w regulaminie), więc nie ma sekcji opłat.

## 6, 7, 8: wspólne

Pliki generuje `golden/build_golden_6_7_8.py`. Uruchom z `backend/`: `uv run python tests/evals/dataset/golden/build_golden_6_7_8.py`. Identyfikatory są losowe, więc każde uruchomienie zmienia całe pliki. Skrypt nie idzie przez `compose`: strony „Dane”, „Kontakt i zgody” i „Strona końcowa” biorą bloki z `domain/blocks/pages.py`, a strony z przedmiotem wniosku są napisane ręcznie.

Decyzje wspólne dla trzech formularzy:

- **Kilka stron z przedmiotem wniosku** w formularzach 6 i 8, tematycznie (Standardy: grupuj pola w sekcjach, strony nazywaj według treści). Pola idą w kolejności dokumentu (K-14).
- **Adres inny niż wnioskodawcy** (osoba odpowiedzialna, miejsce utrzymywania psów, współmałżonek, adres do korespondencji) to blok adresu ze Standardów (szablon `adres_zamieszkania`) z sufiksem w techName (`kraj_korespondencja`, `ulica_korespondencja_zagranica` …) i warunkami przepisanymi na nową sekcję i stronę. Bez danych inicjalnych z MLPZ: rejestr zna tylko adres wnioskodawcy (tak jak adres innej osoby we wzorcach).
- **Sekcja powtarzająca się** (`REPEATING_SECTION`) tam, gdzie papier zbiera te same dane wiele razy. Warunek pola w tym samym wierszu sekcji ma szablon z reguł technicznych: `...field.__userAnswer[$repeatingSectionIndex]['pole' in fieldTechName].answers`.
- **Pola wyliczane** (m², sumy opłat): JSON nie ma typu „formuła”, więc są to pola NUMBER wypełniane przez użytkownika. Wzór jest w opisie pola, stawki też (stawka to stała, nie pole).
- **Zgody.** Pierwsza pozycja to zawsze zgoda z linkiem do klauzuli informacyjnej z szablonu. Oświadczenia z papieru są kolejnymi pozycjami, a sekcja ma wtedy tytuł „Zgody i oświadczenia”. Pełna klauzula RODO, podpis, data i „wypełnia organ” są pominięte.
- **Opłata skarbowa za wniosek** (formularz 7) to sekcja na stronie „Kontakt i zgody” przed zgodami (Standardy: opłaty na przedostatniej stronie). `compose` stawia opłaty na stronie z przedmiotem wniosku; metryki dopasowują pola po techName, więc strona nie wpływa na wynik.
- **Pełnomocnictwo i opłata 17 zł** za pełnomocnictwo pochodzą z bloków predefiniowanych, a nie z listy załączników.

## 6. Zezwolenie na zajęcie pasa drogowego

Źródło: `data/6. .../Wniosek o wydanie zezwolenia na zajęcie pasa drogowego.docx`. 5 stron, 24 sekcje, 82 pola (z blokami predefiniowanymi).

| Strona | Sekcje | Warunek `SHOW` |
| --- | --- | --- |
| Dane | bloki dla `SELF`, `OTHER_PERSON`, `LEGAL_ENTITY`; „Urząd Miasta i Gminy Miasteczko” | bloki |
| Zajęcie pasa drogowego | Lokalizacja robót, Zakres robót, Powierzchnia zajęcia pasa drogowego (`REPEATING_SECTION`), Całkowita powierzchnia zajęcia, Termin robót | – |
| Wykonawca i załączniki | Wykonawca robót, Osoba odpowiedzialna za wykonanie robót, Adres zamieszkania osoby odpowiedzialnej, Załączniki | projekt organizacji ruchu przy „Tak”, informacja o zabezpieczeniu robót przy „Nie” |
| Kontakt i zgody | Dane do kontaktu, Zgoda | – |
| Strona końcowa | Podgląd | – |

Decyzje do przeglądu:

- **Wnioskodawca:** papier ma „imię i nazwisko lub nazwa firmy”, więc wszystkie trzy opcje „Podmiotu wniosku” (Standardy).
- **Powierzchnie:** papier ma 4 kategorie (jezdnia do 20%, 20–50%, powyżej 50%, chodnik) × 2 wiersze. W JSON-ie jeden wiersz `REPEATING_SECTION` = jeden zajmowany fragment: RADIO z kategorią, długość, szerokość i powierzchnia w m² (NUMBER). Całkowita powierzchnia i liczba dni są polami NUMBER, choć dają się wyliczyć.
- **Załączniki 4 i 5** są warunkowe („jeżeli zajęcie wpływa na ruch…” / „jeżeli nie jest wymagany projekt”), więc dochodzi RADIO „Czy zajęcie pasa drogowego wpływa na ruch drogowy?”, a od niego zależą oba pliki.
- **Zgoda z papieru** („Wyrażam zgodę na przetwarzanie… danych osobowych”) to ta sama zgoda co w szablonie, więc sekcja zgód zostaje domyślna.

## 7. Zezwolenie na hodowanie lub utrzymywanie psów (charty)

Źródło: `data/7. .../...ODS` (formularz nie ma DOCX). 4 strony, 16 sekcji, 60 pól.

| Strona | Sekcje | Warunek `SHOW` |
| --- | --- | --- |
| Dane | bloki dla `SELF`, `OTHER_PERSON`; „Urząd Miejski Wrocławia, Wydział Środowiska” | bloki |
| Informacje o psach | Zakres wniosku, Informacje o psie (`REPEATING_SECTION`), Adres miejsca utrzymywania psów, Warunki utrzymywania psów | numer identyfikacyjny przy mikroprocesorze lub tatuażu (w wierszu sekcji powtarzającej się) |
| Kontakt i zgody | Dane do kontaktu, Opłata skarbowa za zezwolenie (82 zł), Zgody i oświadczenia (klauzula + 3 oświadczenia) | – |
| Strona końcowa | Podgląd | – |

Decyzje do przeglądu:

- **K-12:** tytuł przepisany z dokumentu bez zmian („psów ras uznawanych za agresywne”), a pola wzięte z treści, która dotyczy chartów i ich mieszańców (prawo łowieckie). To znana niespójność danych wejściowych.
- **Wnioskodawca:** papier ma tylko dane osoby fizycznej, więc „Swoim” i „Innej osoby” (Standardy).
- **„hodowanie/utrzymywanie\*”** to RADIO, a **„charta/chartów lub mieszańca\*”** to CHECKBOX (rasowy, mieszaniec), bo wniosek może obejmować oba rodzaje psów. Liczbę psów daje sekcja powtarzająca się („w przypadku więcej niż jednego psa pobrać odpowiednią liczbę tabel B”).
- **Pochodzenie psa** rozbite na numer metryki i numer rodowodu (opcjonalne, `**` na papierze) oraz imię, nazwisko i adres poprzedniego właściciela. Adres poprzedniego właściciela to jedno pole tekstowe: blok adresu nie zmieści się w sekcji powtarzającej się (sekcji nie można zagnieżdżać).
- **„Data szczepienia (w przypadku jego braku)”** jest niejasna, więc pole jest opcjonalne. Kopia zaświadczenia o szczepieniu (oświadczenie 2: „w załączeniu kopia dla każdego psa”) to plik w każdym wierszu sekcji psa.
- **Sposób oznakowania:** RADIO mikroprocesor / tatuaż / brak; numer identyfikacyjny widoczny, gdy pies jest oznakowany.

## 8. Deklaracja o wysokości opłaty za gospodarowanie odpadami komunalnymi

Źródło: `data/8. .../Deklaracja o wysokości opłaty.docx`. 6 stron, 30 sekcji, 116 pól.

| Strona | Sekcje | Warunek `SHOW` |
| --- | --- | --- |
| Dane | bloki dla `SELF`, `OTHER_PERSON`, `LEGAL_ENTITY`; „Organ, …”: Prezydent Miasta Gdyni | bloki |
| Składający deklarację | Składający deklarację (B.1), Dane współmałżonka i jego adres (B.2), Korespondencja + Adres do korespondencji (B.4) | współmałżonek przy „Współwłaściciel (wspólność majątkowa)”; opis podmiotu przy „Inny podmiot”; adres przy „Tak” |
| Okoliczności i nieruchomość | Okoliczności złożenia deklaracji (C), Adres nieruchomości (D.1), Miejsce gromadzenia odpadów (D.2), Dane nieruchomości (D.3), Kompostownik (D.4) | daty według okoliczności; D.2 przy budynku wielolokalowym; D.4 przy jednorodzinnym |
| Wysokość opłaty | Obliczenie wysokości opłaty (E.1), … z kompostownikiem (E.2), Opłata za część niezamieszkaną (E.3), Razem (E.4), Załączniki (G) | E.1: wielolokalowy lub brak kompostownika; E.2: jednorodzinny i kompostownik; E.3 i załącznik A/B: część niezamieszkana (A przy jednorodzinnym, B przy wielolokalowym) |
| Kontakt i zgody | Dane do kontaktu (F), Zgody i oświadczenia (klauzula + zgoda na korespondencję e-mail, opcjonalna) | – |
| Strona końcowa | Podgląd | – |

Decyzje do przeglądu:

- **Składający (B.1)** ma 6 opcji, więc SELECT (Standardy: powyżej 5 opcji lista rozwijana). Imię, nazwisko, PESEL, NIP/REGON i adres B.3 dają bloki predefiniowane („Twoje dane”, „Dane podmiotu”, adresy). Pełnomocnik jest w objaśnieniu 13, więc jest też opcja „Innej osoby”.
- **Adres do korespondencji (B.4)** „wypełnić, gdy inny niż B.3”: RADIO Tak/Nie i blok adresu z `SHOW`.
- **Okoliczności (C):** RADIO z 4 opcjami i daty z `SHOW`. Opcje 2 i 4 mają na papierze tę samą datę („data wystąpienia zmiany danych”), więc jest jedno pole widoczne przy obu.
- **Adres nieruchomości (D.1):** miejscowość „Gdynia” jest nadrukowana, więc pole ma wartość domyślną i `readOnly`. Bez bloku adresu ze Standardów (kraj, TERYT), bo deklaracja dotyczy tylko Gdyni.
- **D.2 przed D.3**, jak w dokumencie, choć D.2 zależy od rodzaju nieruchomości z D.3. Pola D.2 są opcjonalne, bo papier każe je wypełnić tylko przy osobnej deklaracji dla części budynku.
- **Kompostownik (D.4)** na papierze to kratka „Oświadczam, że…”. Od niej zależy, które obliczenie opłaty się pokazuje, a sekcja zgód nie może sterować warunkiem, więc to RADIO z pytaniem.
- **Obliczenie opłaty (E.1, E.2):** dla każdej powierzchni lokalu liczba gospodarstw i wysokość opłaty (NUMBER, opcjonalne), stawka w opisie. Suma (poz. 51 / 67), kwota z załącznika (poz. 68) i razem (poz. 69) są wymagane, gdy sekcja jest widoczna. techName w E.2 mają sufiks `_kompostownik`.
- **Załączniki (G):** TAK/NIE z papieru zamienione na pliki: załącznik A lub B (warunkowo), „Inne załączniki” (opcjonalne). „Dokumenty upoważniające” to blok „Pełnomocnictwo”. Załączniki A i B to osobne formularze; tu tylko je dołączamy.
- **Pominięte:** podstawa prawna, termin składania, pouczenie, objaśnienia (część trafiła do opisów pól), numer działki przy adresie zamieszkania (B.3 poz. 16, blok adresu go nie ma), część H (imię, nazwisko, data, podpisy; dają je „Twoje dane” i podpis elektroniczny), część I (adnotacja organu).

## 9. Stypendium, nagroda lub wyróżnienie sportowe (3 w 1)

Źródło: `data/9. .../Wniosek o przyznanie stypendium.docx`. Plik generuje `golden/build_golden_9.py` (szkic `FormDraft` → `compose`, potem ręczne poprawki). Uruchom z `backend/`: `uv run python tests/evals/dataset/golden/build_golden_9.py`. Identyfikatory są losowe, więc każde uruchomienie zmienia cały plik.

Struktura (K-13: jeden JSON, `flow` liniowy przez 4 strony):

| Strona | Sekcje | Warunek `SHOW` |
| --- | --- | --- |
| Dane | bloki predefiniowane dla `SELF` i `LEGAL_ENTITY`; dodatkowo „Dane kontaktowe klubu” (za „Adres siedziby”) i „Dane pełnomocnika klubu” (przed „Pełnomocnictwo”) | klub; klub i pełnomocnik |
| Informacje o wniosku | Rodzaj wniosku (RADIO), Dane kandydata, Dyscypliny sportowe, Osiągnięcia sportowe, Opinia macierzystego klubu sportowego, Dodatkowe informacje, Dane podopiecznych trenera (`REPEATING_SECTION`), Wymagane zaświadczenia | Dyscypliny: stypendium; Osiągnięcia: stypendium lub nagroda; Podopieczni: wyróżnienie; reszta zawsze |
| Kontakt i zgody | Dane do kontaktu, trzy sekcje zgód (po jednej na wariant) | wariant z „Rodzaj wniosku” |
| Strona końcowa | Podgląd uzupełnionego wniosku | – |

Decyzje do przeglądu:

- **Wnioskodawca.** „Prezydent Miasta Zgierza” to opcja „Swoim” (wniosek składa uprawniona osoba we własnym imieniu), a „Klub sportowy” to „Osoby prawnej lub jednostki organizacyjnej” z wyborem Reprezentant / Pełnomocnik. Bloki klubu pochodzą z szablonów, więc „Dane podmiotu” wymagają NIP i REGON, których papier nie ma. Adresat: Urząd Miasta Zgierza.
- **Dane reprezentanta i pełnomocnika.** Imię i nazwisko daje „Twoje dane”, telefon „Dane do kontaktu”. Pełnomocnik podaje dodatkowo serię i numer dowodu (`SERIAL_NUMBER_ID_CARD`) i dołącza odpis z KRS. Reprezentant dołącza odpis w bloku „Potwierdzenie, że jesteś reprezentantem”. Pełnomocnictwo i opłata skarbowa to bloki predefiniowane.
- **Korespondencja klubu.** RADIO „Poczta tradycyjna / Skrzynka ePUAP / e-Doręczenia”. Przy poczcie pojawia się wybór adresu, a przy „Inny adres” pole tekstowe. Adres skrzynki ma walidator `EPUAP` albo `ADE`.
- **Sekcje wspólne bez `SHOW`.** Dane kandydata, opinia klubu, dodatkowe informacje i zaświadczenia mają w trzech wariantach te same pola, różnią się tylko słowem (sportowiec / trener). Jedna sekcja zamiast trzech kopii; przy wyróżnieniu kandydatem jest trener (opis sekcji). Przez to w wariantach stypendium i nagroda zaświadczenia stoją po dodatkowych informacjach, a nie przed nimi.
- **Adresy kandydata** jako TEXTAREA. Blok adresu ze Standardów ma stałe techName (`kraj`, `wojewodztwo`), które już zajmuje adres wnioskodawcy.
- **Dyscypliny** według `docs/propozycja-slownika.md`: CHECKBOX ze słownikiem `DYSCYPLINY_SPORTOWE` (`multiLevelTree`, `searchEnabled`, puste `options`). Rodzaj dyscypliny to pierwszy poziom słownika, więc nie ma osobnego pola. „Inna dyscyplina” to opcjonalne TEXT_FIELD bez `SHOW`, bo słownik nie ma pozycji „inna”, od której mógłby zależeć warunek. Oba pola opcjonalne, żeby zawodnik spoza listy mógł złożyć wniosek.
- **Podopieczni trenera.** Papier ma 4 stałe miejsca, w JSON-ie jest `REPEATING_SECTION` (wzorce nie mają przykładu, reguły go dopuszczają).
- **Zgody.** Na papierze podpisuje je kandydat albo rodzic, a formularz zgody przechowuje administrator, więc wnioskodawca składa oświadczenia, że zgody zebrał. Teksty pełnoletni / nieletni są złączone w jedno zdanie. Klauzula informacyjna (pkt 4) jest pierwszą pozycją każdej sekcji zgód. Wariant wyróżnienia ma dodatkowo oświadczenia za podopiecznych (pkt 6).
- **Pominięte:** data sporządzenia, podpis i pieczątka (zastępuje je podpis elektroniczny), nagłówek zarządzenia.
