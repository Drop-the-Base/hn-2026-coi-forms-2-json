# Zbiór ewaluacyjny (ADR-0010, FR-T4)

`golden/<nr>.json` to ręcznie przygotowany wzorcowy JSON formularza nr `<nr>` z katalogu `data/`. Runner `tests/evals/test_evals.py` paruje pliki po nazwie:

```
EVAL_PREDICTED_DIR=<wyniki> EVAL_GOLDEN_DIR=tests/evals/dataset/golden uv run pytest -m evals
```

`tests/unit/test_golden_dataset.py` pilnuje w CI, że każdy złoty plik przechodzi `check_rules` bez ERROR i `check_schema`.

## Jak powstają złote pliki

`drafts/form_<nr>.py` opisuje formularz jako `FormDraft` (pola sprawy w kolejności z dokumentu, warunki, opłaty, zgody, kto składa), składa go przez `compose` i poprawia ręcznie to, czego `compose` nie umie (tytuły stron, techName, opisy, położenie sekcji). Poprawka = zmiana w skrypcie i ponowne uruchomienie z `backend/`:

```
uv run python -m tests.evals.dataset.drafts.form_2
```

Id (UUID) są losowane przy każdym uruchomieniu; zmienia się tylko id, treść zostaje.

Wspólne dla wszystkich formularzy (ze Standardów i decyzji K-05..K-14): strony Dane → sprawa → Kontakt i zgody → Strona końcowa; usuwamy podpis, datę, „wypełnij wielkimi literami”, podstawę prawną i pouczenia; dane wnioskodawcy z papieru zastępują bloki predefiniowane; zgoda RODO z linkiem do klauzuli jest zawsze.

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
