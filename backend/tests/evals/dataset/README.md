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
