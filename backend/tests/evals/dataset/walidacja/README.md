# Zbiór walidacyjny (hold-out, NFR-11, FR-T4)

**Tylko do pomiaru.** Te formularze udają „nowe, nieznane pliki” z obrony. Nie czytamy ich przy pisaniu reguł, promptów i czytników i nic pod nie nie poprawiamy (zasada w `AGENTS.md`). Uruchamiamy `run_eval --forms 10,11,12` i patrzymy na liczby. Spadek na walidacji szukamy i naprawiamy na formularzach 1–9.

Źródła: `data/walidacja/<nr>. .../`, publiczne druki z BIP gmin (dokumenty urzędowe, art. 4 ustawy o prawie autorskim). Złote JSON-y generuje `build.py` (helpery z `golden/build_golden_6_7_8.py`). Uruchom z `backend/`: `uv run python -m tests.evals.dataset.walidacja.build`. Identyfikatory są losowe, więc każde uruchomienie zmienia całe pliki. `tests/unit/test_golden.py` sprawdza je jak `golden/`.

Wspólne decyzje są takie jak w `golden/` (README tam, sekcje 6–8): strony Dane → przedmiot wniosku → Kontakt i zgody → Strona końcowa, adres inny niż wnioskodawcy to blok adresu z sufiksem w techName, pierwsza zgoda to klauzula z szablonu, potem oświadczenia z papieru prostym językiem, bez podpisu, daty i pełnej klauzuli RODO.

| Nr | Formularz | Źródło | Format | Strony / sekcje / pola / SHOW |
| --- | --- | --- | --- | --- |
| 10 | Wniosek o usunięcie wyrobów zawierających azbest (Dłutów) | [samorzad.gov.pl/web/gmina-dlutow](https://samorzad.gov.pl/web/gmina-dlutow/nabor-wnioskow-do-programu-usuwania-i-unieszkodliwiania-wyrobow-zawierajacych-azbest) | DOCX | 5 / 23 / 77 / 39 |
| 11 | Wniosek o zwrot kosztów przewozu dziecka z niepełnosprawnością (Gózd) | [samorzad.gov.pl/web/urzad-gminy-w-gozdzie](https://samorzad.gov.pl/web/urzad-gminy-w-gozdzie/zwrot-kosztow-dowozu-uczniow-z-niepelnosprawnosciami) | DOCX | 5 / 22 / 85 / 40 |
| 12 | Wniosek o zezwolenie na usunięcie drzew lub krzewów (Piaseczno) | [bip.piaseczno.eu](https://bip.piaseczno.eu/attachments/download/34132) | PDF | 5 / 20 / 79 / 38 |

Liczby z blokami predefiniowanymi.

Poza walidatorami ze Standardów (`validation_for`) nie ma walidatora numeru rachunku: reguły techniczne go nie znają.

## 10. Azbest (Dłutów)

- **Tytuł**: papier ma „WNIOSEK – AZBEST”, więc tytuł opisowy z treści („proszę o zakwalifikowanie … wyrobów zawierających azbest”).
- **Kto składa**: imię i nazwisko albo nazwa, NIP, osoba reprezentująca → Swoim, Innej osoby, Osoby prawnej.
- **Strony** w kolejności papieru (K-14): „Nieruchomość i wyroby z azbestem” (adres, działka, zakres, obiekt, wyroby), „Właściciel i załączniki” (tytuł prawny, dane do umowy, załączniki).
- **Nieruchomość**: blok adresu (`*_nieruchomosc`), działka, obręb, księga wieczysta (opcjonalna: nie każda nieruchomość ją ma). Tytuł prawny RADIO z „Inny” → pole tekstowe.
- **Dane do umowy**: imię, nazwisko, PESEL, adres i dane firmy dają bloki. Zostaje seria i numer dowodu (walidator `SERIAL_NUMBER_ID_CARD`, jak w nr 9), widoczne, gdy wnioskodawca nie jest osobą prawną.
- **Zakres zadania**: RADIO z dwiema kratkami papieru. „Demontaż z budynku ……” i „Rodzaj obiektu” pytają o to samo, więc jest jedno pole „Rodzaj obiektu” (TEXT_FIELD, przykłady w opisie, bo lista kończy się na „itp.”).
- **Załączniki**: załącznik nr 2 to oświadczenie, że wnioskodawca dostarczy zgłoszenie robót lub pozwolenie na budowę (osobny druk gminy). Kopia pozwolenia na wymianę pokrycia widoczna przy demontażu, oświadczenie de minimis przy obiekcie związanym z działalnością. Klauzula informacyjna nie jest plikiem.
- **Oświadczenia**: 4 wymagane, w czasie teraźniejszym lub przyszłym, bez form rodzajowych.

## 11. Zwrot kosztów przewozu (Gózd)

- **Kto składa**: rodzic (dane osoby) → Swoim albo Innej osoby. Telefon i e-mail → Dane do kontaktu (opcjonalne, jak na papierze).
- **Dziecko**: imię i nazwisko rozbite na dwa pola, adres dziecka i placówki to bloki adresu.
- **Orzeczenie**: papier ma dwa wiersze (kształcenie specjalne, zajęcia rewalidacyjno-wychowawcze) z tymi samymi danymi, więc RADIO z rodzajem i jeden zestaw pól.
- **Trasa**: punkty 2–4 papieru („jeśli przewóz odbywa się na trasie do pracy”) → RADIO „Czy przewozisz dziecko w drodze do pracy?” i od niego kilometry oraz adres pracy. Informacja o Mapach Google jest opisem sekcji.
- **Dni przewozu**: „w wybrane dni tygodnia” → CHECKBOX pon.–pt.
- **Sposób wypłaty**: papier ma jedną kratkę (przelew), więc tylko numer rachunku.
- **Oświadczenia**: parametry pojazdu (badanie, OC, NNW), oryginały dokumentów, zgoda na dane o zdrowiu (wymagana), art. 233 KK. Zgoda na dane kontaktowe pominięta: kontakt jest opcjonalny w bloku.

## 12. Usunięcie drzew lub krzewów (Piaseczno)

- **Adresat**: papier ma tylko wydział w stopce → „Urząd Miasta i Gminy Piaseczno, Wydział Ochrony Środowiska i Gospodarki Rolnej”.
- **Kto składa**: „imię i nazwisko / nazwa”, „adres zamieszkania / siedziby” → wszystkie trzy opcje.
- **Drzewa i krzewy**: `REPEATING_SECTION`, wiersz = jedna roślina. Obwód pnia przy „Drzewo”, powierzchnia przy „Krzew” (warunek w wierszu sekcji). Przypis o kilku pniach w opisie pola.
- **Załącznik 3** („usunięcie wynika / nie wynika z działalności gospodarczej”) to pytanie RADIO, a nie plik.
- **Przeznaczenie terenu**: działka leśna idzie do Nadleśnictwa, więc nie jest opcją, tylko informacją w opisie.
- **Adres nieruchomości** tylko, gdy inny niż wnioskodawcy (przypis papieru).
- **Załączniki**: 1 i 2 wymagane, 4–10 opcjonalne z warunkiem z papieru w opisie (papier: „właściwe zakreślić”). Papier nie ma oświadczeń, więc zostaje tylko klauzula.
