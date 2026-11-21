# Zbiór ewaluacyjny (FR-T4, ADR-0010)

`golden/<nr formularza>.json` to złoty JSON, przygotowany ręcznie według Standardów i reguł technicznych. Runner (`tests/evals/test_evals.py`) paruje go z predykcją o tej samej nazwie pliku. `tests/unit/test_golden.py` sprawdza każdy plik z `golden/`: reguły bez ERROR, brak odwołań w `states` do nieistniejących pól i stron, oficjalny schemat.

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
