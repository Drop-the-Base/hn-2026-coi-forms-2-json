"""Builds the hold-out goldens 10.json, 11.json and 12.json (FR-T4, NFR-11). See README.md here.

Measurement only: never tune readers, rules or prompts to these forms (AGENTS.md).
Run from backend/: uv run python -m tests.evals.dataset.walidacja.build
Ids are random, so every run rewrites the whole files.
"""

from pathlib import Path

from forms2json.domain.blocks.pages import APPLICANT_TAB, FOR_WHOM, LEGAL_ENTITY
from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.jsonata import answer_is, answer_is_not
from forms2json.domain.rules import Severity, _walk, check_rules
from forms2json.domain.standards import check_schema, check_standards
from tests.evals.dataset.golden.build_golden_6_7_8 import (
    YES_NO,
    K,
    address,
    contact,
    field,
    form,
    page,
    repeated_answer_is,
    section,
)

OUT = Path(__file__).parent


def form_10() -> FormDefinition:
    t2, t3 = "Nieruchomość", "Wyroby zawierające azbest"
    demolition = "Demontaż, zbieranie, transport i unieszkodliwienie wyrobów"
    business = "Związany z działalnością gospodarczą, w tym rolniczą"
    other_title = "Inny"
    estate = page(
        t2,
        [
            address("adres_nieruchomosci", "Adres nieruchomości", t2, "nieruchomosc"),
            section(
                "dane_ewidencyjne_nieruchomosci",
                "Dane ewidencyjne nieruchomości",
                [
                    field(
                        "TEXT_FIELD",
                        "numer_dzialki_ewidencyjnej",
                        "Numer działki ewidencyjnej",
                        True,
                    ),
                    field("TEXT_FIELD", "obreb_geodezyjny", "Obręb geodezyjny", True),
                    field("TEXT_FIELD", "numer_ksiegi_wieczystej", "Numer księgi wieczystej"),
                ],
            ),
            section(
                "prawo_do_nieruchomosci",
                "Prawo do dysponowania nieruchomością",
                [
                    field(
                        "RADIO",
                        "forma_prawna_wlasciciela",
                        "Forma prawna właściciela obiektu",
                        True,
                        [
                            "Osoba fizyczna",
                            "Osoba prawna",
                            "Jednostka organizacyjna nieposiadająca osobowości prawnej",
                        ],
                    ),
                    field(
                        "RADIO",
                        "tytul_prawny_do_nieruchomosci",
                        "Na jakiej podstawie dysponujesz nieruchomością?",
                        True,
                        ["Własność", "Współwłasność", "Użytkowanie wieczyste", other_title],
                    ),
                    field(
                        "TEXT_FIELD",
                        "inny_tytul_prawny",
                        "Opisz inny tytuł prawny",
                        True,
                        when=answer_is(
                            other_title,
                            t2,
                            "prawo_do_nieruchomosci",
                            "tytul_prawny_do_nieruchomosci",
                        ),
                    ),
                ],
            ),
            section(
                "dane_do_umowy",
                "Dane do umowy",
                [
                    field(
                        "TEXT_FIELD",
                        "seria_i_numer_dowodu_osobistego",
                        "Seria i numer dowodu osobistego",
                        True,
                    )
                ],
                "Podaj dane osoby, z którą gmina zawrze umowę.",
                when=answer_is_not(LEGAL_ENTITY, APPLICANT_TAB, "podmiot_wniosku", FOR_WHOM),
            ),
        ],
    )
    scope = answer_is(demolition, t3, "zakres_zadania", "zakres_zadania_azbest")
    for_business = answer_is(business, t3, "obiekt_z_azbestem", "przeznaczenie_obiektu")
    asbestos = page(
        t3,
        [
            section(
                "zakres_zadania",
                "Zakres zadania",
                [
                    field(
                        "RADIO",
                        "zakres_zadania_azbest",
                        "Wybierz zakres zadania",
                        True,
                        [
                            demolition,
                            "Zbieranie, transport i unieszkodliwienie wcześniej "
                            "zdemontowanych wyrobów",
                        ],
                    )
                ],
                "Gmina Dłutów może odstąpić od zadania, jeśli nie dostanie dofinansowania "
                "z WFOŚiGW w Łodzi.",
            ),
            section(
                "obiekt_z_azbestem",
                "Obiekt, na którym jest azbest",
                [
                    field(
                        "TEXT_FIELD",
                        "rodzaj_obiektu",
                        "Rodzaj obiektu",
                        True,
                        description="Na przykład budynek mieszkalny, gospodarczy, inwentarski, "
                        "garaż, wiata, obiekt małej architektury.",
                    ),
                    field(
                        "RADIO",
                        "przeznaczenie_obiektu",
                        "Przeznaczenie obiektu",
                        True,
                        [business, "Niezwiązany z działalnością gospodarczą, w tym rolniczą"],
                    ),
                ],
            ),
            section(
                "wyroby_zawierajace_azbest",
                "Wyroby zawierające azbest",
                [
                    field(
                        "TEXT_FIELD",
                        "rodzaj_wyrobow",
                        "Rodzaj wyrobów zawierających azbest",
                        True,
                        description="Na przykład płyty cementowo-azbestowe faliste lub płaskie.",
                    ),
                    field(
                        "TEXT_FIELD",
                        "sposob_wykorzystania_wyrobow",
                        "Sposób wykorzystania wyrobów",
                        True,
                        description="Na przykład pokrycie dachowe, elewacja, osłona balkonowa.",
                    ),
                    field(
                        "TEXT_FIELD",
                        "ilosc_wyrobow",
                        "Ilość wyrobów zawierających azbest",
                        True,
                        description="Dla budynku podaj m² lub tony, dla płyt liczbę sztuk "
                        "i wymiar płyty.",
                    ),
                ],
            ),
            section(
                "zalaczniki",
                "Załączniki",
                [
                    field(
                        "FILE_UPLOADER",
                        "ocena_stanu_wyrobow",
                        "Ocena stanu i możliwości bezpiecznego użytkowania wyrobów "
                        "zawierających azbest",
                        True,
                    ),
                    field("FILE_UPLOADER", "oswiadczenie_zalacznik_2", "Oświadczenie", True),
                    field(
                        "FILE_UPLOADER",
                        "pozwolenie_na_wymiane_pokrycia",
                        "Kopia pozwolenia lub zgłoszenia wymiany pokrycia dachowego z mapą",
                        True,
                        when=scope,
                    ),
                    field(
                        "FILE_UPLOADER",
                        "oswiadczenie_de_minimis",
                        "Oświadczenie o pomocy de minimis",
                        True,
                        when=for_business,
                    ),
                ],
            ),
        ],
    )
    statements = [
        (
            "Po demontażu zabezpieczę dach i wykonam nowe pokrycie dachowe we własnym zakresie "
            "i na własny koszt.",
            True,
        ),
        (
            "Zgadzam się na kontrolę pracowników Urzędu Gminy w Dłutowie na nieruchomości "
            "z wniosku przed zadaniem, w trakcie i po jego zakończeniu.",
            True,
        ),
        (
            "Znam i przyjmuję warunki udziału w zadaniu określone przez WFOŚiGW w Łodzi. "
            "Zgadzam się na zawarcie przez WFOŚiGW w Łodzi umowy dotacji z Gminą Dłutów.",
            True,
        ),
        (
            "Zgadzam się, żeby firma, która usunie azbest, weszła na teren mojej nieruchomości.",
            True,
        ),
    ]
    return form(
        "Wniosek o usunięcie wyrobów zawierających azbest",
        "Wójt Gminy Dłutów",
        [K.SELF, K.OTHER_PERSON, K.LEGAL_ENTITY],
        [estate, asbestos],
        contact(statements),
    )


def form_11() -> FormDefinition:
    t2, t3 = "Dziecko i placówka", "Przewóz dziecka"
    on_way = answer_is("Tak", t3, "trasa_przewozu", "przewoz_w_drodze_do_pracy")
    chosen_days = "W wybrane dni tygodnia"
    child = page(
        t2,
        [
            section(
                "dane_dziecka",
                "Dane dziecka",
                [
                    field("TEXT_FIELD", "imie_dziecka", "Imię dziecka", True),
                    field("TEXT_FIELD", "nazwisko_dziecka", "Nazwisko dziecka", True),
                ],
            ),
            address("adres_zamieszkania_dziecka", "Adres zamieszkania dziecka", t2, "dziecko"),
            section(
                "placowka",
                "Przedszkole, szkoła lub ośrodek",
                [
                    field(
                        "TEXT_FIELD",
                        "nazwa_placowki",
                        "Nazwa przedszkola, szkoły lub ośrodka",
                        True,
                    ),
                    field(
                        "TEXT_FIELD",
                        "rok_szkolny",
                        "Rok szkolny",
                        True,
                        description="Na przykład 2025/2026.",
                    ),
                ],
            ),
            address("adres_placowki", "Adres przedszkola, szkoły lub ośrodka", t2, "placowka"),
            section(
                "orzeczenie",
                "Orzeczenie",
                [
                    field(
                        "RADIO",
                        "rodzaj_orzeczenia",
                        "Rodzaj orzeczenia",
                        True,
                        [
                            "O potrzebie kształcenia specjalnego",
                            "O potrzebie zajęć rewalidacyjno-wychowawczych",
                        ],
                    ),
                    field("TEXT_FIELD", "numer_orzeczenia", "Numer orzeczenia", True),
                    field("DATEPICKER", "data_orzeczenia", "Data wydania orzeczenia", True),
                    field(
                        "TEXT_FIELD",
                        "organ_wydajacy_orzeczenie",
                        "Kto wydał orzeczenie",
                        True,
                        description="Na przykład nazwa poradni psychologiczno-pedagogicznej.",
                    ),
                    field(
                        "TEXT_FIELD",
                        "okres_orzeczenia",
                        "Na jaki okres wydano orzeczenie",
                        True,
                    ),
                ],
            ),
        ],
    )
    transport = page(
        t3,
        [
            section(
                "trasa_przewozu",
                "Trasa przewozu",
                [
                    field("TEXTAREA", "opis_trasy", "Opis trasy przewozu", True),
                    field(
                        "NUMBER",
                        "km_dom_placowka",
                        "Liczba kilometrów z domu do placówki w jedną stronę",
                        True,
                    ),
                    field(
                        "RADIO",
                        "przewoz_w_drodze_do_pracy",
                        "Czy przewozisz dziecko w drodze do pracy?",
                        True,
                        YES_NO,
                    ),
                    field(
                        "NUMBER",
                        "km_placowka_praca",
                        "Liczba kilometrów z placówki do miejsca pracy w jedną stronę",
                        True,
                        when=on_way,
                    ),
                    field(
                        "NUMBER",
                        "km_dom_praca",
                        "Liczba kilometrów z domu do miejsca pracy w jedną stronę",
                        True,
                        when=on_way,
                    ),
                ],
                "Urząd przyjmie liczbę kilometrów najkrótszej trasy z Map Google "
                "dla podanych adresów.",
            ),
            address("adres_miejsca_pracy", "Adres miejsca pracy", t3, "praca", on_way),
            section(
                "pojazd",
                "Pojazd",
                [
                    field("TEXT_FIELD", "marka_model_rocznik", "Marka, model i rocznik", True),
                    field("TEXT_FIELD", "numer_rejestracyjny", "Numer rejestracyjny", True),
                    field("NUMBER", "pojemnosc_silnika", "Pojemność silnika w cm³", True),
                ],
            ),
            section(
                "okres_przewozu",
                "Okres przewozu",
                [
                    field(
                        "RADIO",
                        "czestotliwosc_przewozu",
                        "Jak często przewozisz dziecko?",
                        True,
                        ["Codziennie w dni robocze", chosen_days],
                    ),
                    field(
                        "CHECKBOX",
                        "dni_przewozu",
                        "Wybierz dni tygodnia",
                        True,
                        ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"],
                        when=answer_is(chosen_days, t3, "okres_przewozu", "czestotliwosc_przewozu"),
                    ),
                    field("DATEPICKER", "data_rozpoczecia_przewozu", "Data rozpoczęcia", True),
                    field("DATEPICKER", "data_zakonczenia_przewozu", "Data zakończenia", True),
                ],
            ),
            section(
                "sposob_wyplaty",
                "Sposób wypłaty",
                [field("TEXT_FIELD", "numer_rachunku", "Numer rachunku bankowego", True)],
            ),
            section(
                "zalaczniki",
                "Załączniki",
                [
                    field(
                        "FILE_UPLOADER",
                        "zaswiadczenie_z_placowki",
                        "Zaświadczenie z placówki o uczęszczaniu dziecka w roku szkolnym",
                        True,
                    ),
                    field("FILE_UPLOADER", "kopia_orzeczenia", "Kopia orzeczenia", True),
                ],
            ),
        ],
    )
    statements = [
        ("Samochód jest sprawny technicznie i ma aktualne badanie techniczne.", True),
        ("Mam aktualne ubezpieczenie OC samochodu.", True),
        ("Mam aktualne ubezpieczenie NNW.", True),
        ("Na wezwanie urzędu pokażę oryginały dokumentów, z których pochodzą dane.", True),
        (
            "Zgadzam się na przetwarzanie przez Urząd Gminy Gózd informacji o stanie zdrowia "
            "dziecka z orzeczenia.",
            True,
        ),
        (
            "Znam odpowiedzialność karną za podanie nieprawdy (art. 233 § 1 Kodeksu karnego). "
            "Dane we wniosku są prawdziwe.",
            True,
        ),
    ]
    return form(
        "Wniosek o zwrot rodzicowi kosztów przewozu dziecka z niepełnosprawnością "
        "do przedszkola, szkoły lub ośrodka",
        "Wójt Gminy Gózd",
        [K.SELF, K.OTHER_PERSON],
        [child, transport],
        contact(statements),
    )


def form_12() -> FormDefinition:
    t2, t3 = "Drzewa i krzewy", "Miejsce i załączniki"
    plants = "drzewa_i_krzewy"
    is_tree = repeated_answer_is("Drzewo", t2, plants, "rodzaj_rosliny")
    is_bush = repeated_answer_is("Krzew", t2, plants, "rodzaj_rosliny")
    elsewhere = answer_is("Tak", t3, "miejsce_usuniecia", "inny_adres_nieruchomosci")
    trees = page(
        t2,
        [
            section(
                plants,
                "Drzewa i krzewy do usunięcia",
                [
                    field(
                        "RADIO", "rodzaj_rosliny", "Co chcesz usunąć?", True, ["Drzewo", "Krzew"]
                    ),
                    field("TEXT_FIELD", "nazwa_gatunku", "Nazwa gatunku", True),
                    field(
                        "TEXT_FIELD",
                        "obwod_pnia",
                        "Obwód pnia na wysokości 130 cm",
                        True,
                        description="Jeśli drzewo ma kilka pni, podaj obwód każdego z nich. "
                        "Jeśli na tej wysokości nie ma pnia, zmierz obwód tuż pod koroną.",
                        when=is_tree,
                    ),
                    field(
                        "NUMBER",
                        "powierzchnia_krzewu",
                        "Powierzchnia, z której usuniesz krzew, w m²",
                        True,
                        when=is_bush,
                    ),
                ],
                "Dodaj każde drzewo i każdy krzew, który chcesz usunąć.",
                repeating=True,
            ),
            section(
                "przyczyna_i_termin",
                "Przyczyna i termin usunięcia",
                [
                    field("TEXTAREA", "przyczyna_usuniecia", "Przyczyna usunięcia", True),
                    field("DATEPICKER", "termin_usuniecia", "Planowany termin usunięcia", True),
                    field(
                        "RADIO",
                        "cel_dzialalnosc_gospodarcza",
                        "Czy usunięcie wynika z celu związanego z działalnością gospodarczą?",
                        True,
                        YES_NO,
                    ),
                ],
            ),
        ],
    )
    place = page(
        t3,
        [
            section(
                "miejsce_usuniecia",
                "Miejsce usunięcia",
                [
                    field(
                        "TEXT_FIELD",
                        "numer_dzialki_ewidencyjnej",
                        "Numer działki ewidencyjnej",
                        True,
                    ),
                    field(
                        "RADIO",
                        "przeznaczenie_terenu",
                        "Przeznaczenie terenu",
                        True,
                        ["Działka budowlana", "Działka rolna", "Inne"],
                        description="Wniosek o usunięcie drzewa z działki leśnej złóż "
                        "w Nadleśnictwie Chojnów.",
                    ),
                    field(
                        "RADIO",
                        "inny_adres_nieruchomosci",
                        "Czy nieruchomość ma inny adres niż Twój?",
                        True,
                        YES_NO,
                    ),
                ],
            ),
            address("adres_nieruchomosci", "Adres nieruchomości", t3, "nieruchomosc", elsewhere),
            section(
                "zalaczniki",
                "Załączniki",
                [
                    field(
                        "FILE_UPLOADER",
                        "oswiadczenie_o_tytule_prawnym",
                        "Oświadczenie o tytule prawnym do nieruchomości",
                        True,
                    ),
                    field(
                        "FILE_UPLOADER",
                        "rysunek_lub_mapa",
                        "Rysunek lub mapa z położeniem drzew i krzewów",
                        True,
                    ),
                    field(
                        "FILE_UPLOADER",
                        "oswiadczenie_o_wlasnosci_urzadzen",
                        "Oświadczenie o prawie własności urządzeń",
                        description="Jeśli drzewo lub krzew zagraża urządzeniom, o których mowa "
                        "w art. 49 § 1 Kodeksu cywilnego.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "zgoda_wlasciciela",
                        "Zgoda właściciela nieruchomości",
                        description="Jeśli nie jesteś właścicielem nieruchomości.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "projekt_zagospodarowania",
                        "Projekt zagospodarowania działki lub terenu",
                        description="Jeśli wymaga go Prawo budowlane.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "oswiadczenie_spoldzielnia_wspolnota",
                        "Oświadczenie o poinformowaniu członków spółdzielni lub wspólnoty "
                        "mieszkaniowej",
                        description="Jeśli wniosek składa spółdzielnia lub wspólnota mieszkaniowa.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "projekt_nasadzen_zastepczych",
                        "Projekt planu nasadzeń zastępczych lub przesadzenia",
                        description="Jeśli je planujesz.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "decyzja_srodowiskowa",
                        "Decyzja o środowiskowych uwarunkowaniach lub postanowienie "
                        "w sprawie obszaru Natura 2000",
                        description="Jeśli są wymagane dla przedsięwzięcia.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "zezwolenie_gatunki_chronione",
                        "Zezwolenie dotyczące gatunków chronionych",
                        description="Jeśli zostało wydane.",
                    ),
                ],
            ),
        ],
    )
    return form(
        "Wniosek o wydanie zezwolenia na usunięcie drzew lub krzewów",
        "Urząd Miasta i Gminy Piaseczno, Wydział Ochrony Środowiska i Gospodarki Rolnej",
        [K.SELF, K.OTHER_PERSON, K.LEGAL_ENTITY],
        [trees, place],
        contact(),
    )


def main() -> None:
    for name, build in (("10", form_10), ("11", form_11), ("12", form_12)):
        golden = build()
        tech_names = [p.field.tech_name for p in _walk(golden)]
        assert len(tech_names) == len(set(tech_names)), f"{name}: duplicate techName"
        issues = check_rules(golden) + check_standards(golden) + check_schema(golden.to_dict())
        assert not [i for i in issues if i.severity is Severity.ERROR], issues
        for issue in issues:
            print(f"{name}: {issue.code} {issue.message}")
        (OUT / f"{name}.json").write_text(golden.to_json() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
