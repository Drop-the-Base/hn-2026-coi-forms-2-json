"""Builds 6.json, 7.json and 8.json (FR-T4) from the house blocks plus hand-written subject pages.

Not via compose: these forms need several subject pages, REPEATING_SECTION, address blocks under
new techNames and fees on the contact page, which compose does not do.

Run from backend/: uv run python tests/evals/dataset/golden/build_golden_6_7_8.py
Ids are random, so every run rewrites the whole files; decisions: dataset/README.md, sections 6-8.
"""

from collections.abc import Sequence
from itertools import pairwise
from pathlib import Path

from forms2json.domain.blocks import pages
from forms2json.domain.blocks.pages import applicant_page, contact_page, finish_page
from forms2json.domain.compose import EMPTY_HTML
from forms2json.domain.form_definition import Field, FlowLink, FormDefinition, Option, Question, Tab
from forms2json.domain.form_draft import ApplicantKind
from forms2json.domain.jsonata import all_of, answer_is, any_of, show
from forms2json.domain.layout import layout_page, new_id, slugify
from forms2json.domain.rules import Severity, _walk, check_rules
from forms2json.domain.standards import check_schema, check_standards
from forms2json.domain.validators import validation_for

GOLDEN = Path(__file__).parent
YES_NO = ("Tak", "Nie")
K = ApplicantKind


def html(text: str) -> str:
    return pages._html(text)


def field(
    type_: str,
    tech_name: str,
    title: str,
    required: bool = False,
    options: Sequence[str] = (),
    description: str = "",
    when: str | None = None,
) -> Question:
    f = Field(
        id=new_id(),
        type=type_,
        tech_name=tech_name,
        title=title,
        question_order=0,
        description=html(description) if description else "",
        options=[Option(o, o, slugify(o)) for o in options],
        validation=validation_for(title, tech_name, required),
        states=[show(when)] if when else [],
    )
    return Question(0, 0, 1, 1, f)


def section(
    tech_name: str,
    title: str,
    children: list[Question],
    description: str = "",
    when: str | None = None,
    repeating: bool = False,
) -> Question:
    f = Field(
        id=new_id(),
        type="REPEATING_SECTION" if repeating else "SECTION",
        tech_name=tech_name,
        title=title,
        question_order=0,
        description=html(description) if description else EMPTY_HTML,
        repeating_section_grid=children,
        states=[show(when)] if when else [],
    )
    return Question(0, 0, 1, 1, f)


def address(tech_name: str, title: str, tab: str, suffix: str, when: str | None = None) -> Question:
    block = pages.other_address(tech_name, title, tab, suffix)
    block.field.states = [show(when)] if when else []
    return block


def repeated_answer_is(value: str, tab: str, section: str, field: str) -> str:
    """Answer of a field in the same row of a REPEATING_SECTION (template from the rules doc)."""
    return (
        f"(\"{value}\" in tabs['{tab}' in title].questions['{section}' in field.techName]"
        f".field.__userAnswer[$repeatingSectionIndex]['{field}' in fieldTechName].answers)"
    )


def page(title: str, sections: list[Question]) -> Tab:
    layout_page(sections)
    return Tab(new_id(), title, "MAIN", sections)


def contact(consents: Sequence[tuple[str, bool]] = (), fee: Question | None = None) -> Tab:
    """Contact page: the GDPR link consent from the template plus the document's own consents."""
    tab = contact_page()
    consent_section = tab.questions[-1].field
    config = consent_section.repeating_section_grid[0].field.consent_section_config
    assert config is not None and isinstance(config["consents"], list)
    config["consents"] += [{"description": html(t), "required": r} for t, r in consents]
    if consents:
        consent_section.title = "Zgody i oświadczenia"
    if fee:  # Standardy: fees belong to the second to last page, before the consents
        tab.questions.insert(1, fee)
        layout_page(tab.questions)
    return tab


def form(
    title: str, addressee: str, kinds: list[ApplicantKind], subject: list[Tab], last: Tab
) -> FormDefinition:
    tabs = [applicant_page(addressee, kinds), *subject, last, finish_page()]
    links = [FlowLink(new_id(), a.id, b.id) for a, b in pairwise(tabs)]
    return FormDefinition(title, tabs, links)


def form_6() -> FormDefinition:
    t2, t3 = "Zajęcie pasa drogowego", "Wykonawca i załączniki"
    traffic = answer_is("Tak", t3, "zalaczniki", "czy_zajecie_wplywa_na_ruch")
    no_traffic = answer_is("Nie", t3, "zalaczniki", "czy_zajecie_wplywa_na_ruch")
    road = page(
        t2,
        [
            section(
                "lokalizacja_robot",
                "Lokalizacja robót",
                [
                    field("TEXT_FIELD", "nazwa_i_numer_drogi", "Nazwa i numer drogi gminnej", True),
                    field("TEXT_FIELD", "miejscowosc_robot", "Miejscowość", True),
                    field(
                        "TEXT_FIELD", "numer_ewidencyjny_dzialki", "Numer ewidencyjny działki", True
                    ),
                ],
            ),
            section(
                "zakres_robot",
                "Zakres robót",
                [
                    field(
                        "TEXTAREA",
                        "rodzaj_robot_i_sposob_wykonania",
                        "Rodzaj robót i sposób ich wykonania",
                        True,
                    )
                ],
            ),
            section(
                "powierzchnia_zajecia",
                "Powierzchnia zajęcia pasa drogowego",
                [
                    field(
                        "RADIO",
                        "element_pasa_drogowego",
                        "Zajmowany element pasa drogowego",
                        True,
                        [
                            "Jezdnia, zajęcie do 20% szerokości",
                            "Jezdnia, zajęcie powyżej 20% do 50% szerokości",
                            "Jezdnia, zajęcie powyżej 50% szerokości",
                            "Chodnik",
                        ],
                    ),
                    field("NUMBER", "dlugosc_zajecia", "Długość w m", True),
                    field("NUMBER", "szerokosc_zajecia", "Szerokość w m", True),
                    field(
                        "NUMBER",
                        "powierzchnia_zajecia_elementu",
                        "Powierzchnia w m²",
                        True,
                        description="Pomnóż długość przez szerokość.",
                    ),
                ],
                "Dodaj osobno każdy zajmowany fragment pasa drogowego. Wymiary podaj w metrach.",
                repeating=True,
            ),
            section(
                "calkowita_powierzchnia",
                "Całkowita powierzchnia zajęcia",
                [
                    field(
                        "NUMBER",
                        "calkowita_powierzchnia_zajecia",
                        "Całkowita powierzchnia zajęcia w m²",
                        True,
                        description="Zsumuj powierzchnie wszystkich zajmowanych fragmentów.",
                    )
                ],
            ),
            section(
                "termin_robot",
                "Termin robót",
                [
                    field("DATEPICKER", "data_rozpoczecia_robot", "Data rozpoczęcia robót", True),
                    field("DATEPICKER", "data_zakonczenia_robot", "Data zakończenia robót", True),
                    field(
                        "NUMBER",
                        "liczba_dni_zajecia",
                        "Liczba dni zajęcia pasa drogowego",
                        True,
                        description="Termin musi być zgodny z harmonogramem robót, "
                        "który dodasz jako załącznik.",
                    ),
                ],
            ),
        ],
    )
    contractor = page(
        t3,
        [
            section(
                "wykonawca_robot",
                "Wykonawca robót",
                [
                    field(
                        "TEXT_FIELD",
                        "nazwa_wykonawcy",
                        "Nazwa przedsiębiorstwa lub imię i nazwisko wykonawcy",
                        True,
                    )
                ],
            ),
            section(
                "osoba_odpowiedzialna",
                "Osoba odpowiedzialna za wykonanie robót",
                [
                    field("TEXT_FIELD", "imie_osoba_odpowiedzialna", "Imię", True),
                    field("TEXT_FIELD", "nazwisko_osoba_odpowiedzialna", "Nazwisko", True),
                    field(
                        "TEXT_FIELD", "numer_telefonu_osoba_odpowiedzialna", "Numer telefonu", True
                    ),
                ],
                "Ta osoba odpowiada za wykonanie robót zgodnie z projektem i za odtworzenie "
                "pasa drogowego zgodnie z warunkami zezwolenia.",
            ),
            address(
                "adres_osoby_odpowiedzialnej",
                "Adres zamieszkania osoby odpowiedzialnej",
                t3,
                "osoba_odpowiedzialna",
            ),
            section(
                "zalaczniki",
                "Załączniki",
                [
                    field(
                        "FILE_UPLOADER",
                        "ogolny_plan_orientacyjny",
                        "Ogólny plan orientacyjny",
                        True,
                        description="Plan w skali 1:10 000 lub 1:25 000 z zaznaczonym "
                        "zajmowanym odcinkiem pasa drogowego.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "szczegolowy_plan_sytuacyjny",
                        "Szczegółowy plan sytuacyjny",
                        True,
                        description="Plan w skali 1:1000 lub 1:500 z granicami i wymiarami "
                        "planowanej powierzchni zajęcia pasa drogowego.",
                    ),
                    field(
                        "FILE_UPLOADER", "harmonogram_robot", "Szczegółowy harmonogram robót", True
                    ),
                    field(
                        "RADIO",
                        "czy_zajecie_wplywa_na_ruch",
                        "Czy zajęcie pasa drogowego wpływa na ruch drogowy?",
                        True,
                        YES_NO,
                        "Wybierz Tak, jeśli zajęcie wpływa na ruch drogowy, ogranicza widoczność "
                        "na drodze albo zmienia organizację ruchu pojazdów lub pieszych.",
                    ),
                    field(
                        "FILE_UPLOADER",
                        "projekt_organizacji_ruchu",
                        "Zatwierdzony projekt organizacji ruchu",
                        True,
                        when=traffic,
                    ),
                    field(
                        "FILE_UPLOADER",
                        "informacja_o_zabezpieczeniu_robot",
                        "Informacja o sposobie zabezpieczenia robót",
                        True,
                        when=no_traffic,
                    ),
                ],
            ),
        ],
    )
    return form(
        "Wniosek o wydanie zezwolenia na zajęcie pasa drogowego w celu prowadzenia robót",
        "Urząd Miasta i Gminy Miasteczko",
        [K.SELF, K.OTHER_PERSON, K.LEGAL_ENTITY],
        [road, contractor],
        contact(),
    )


def form_7() -> FormDefinition:
    t2 = "Informacje o psach"
    marking = "sposob_oznakowania_psa"
    marked = any_of(
        repeated_answer_is("Mikroprocesor", t2, "informacje_o_psie", marking),
        repeated_answer_is("Tatuaż", t2, "informacje_o_psie", marking),
    )
    dogs = page(
        t2,
        [
            section(
                "zakres_wniosku",
                "Zakres wniosku",
                [
                    field(
                        "RADIO",
                        "wybierz_o_co_wnioskujesz",
                        "Wybierz, o co wnioskujesz",
                        True,
                        ["Hodowanie", "Utrzymywanie"],
                    ),
                    field(
                        "CHECKBOX",
                        "wybierz_czego_dotyczy_wniosek",
                        "Wybierz, czego dotyczy wniosek",
                        True,
                        ["Chart rasowy", "Mieszaniec charta"],
                    ),
                ],
            ),
            section(
                "informacje_o_psie",
                "Informacje o psie",
                [
                    field("TEXT_FIELD", "numer_metryki", "Numer metryki"),
                    field("TEXT_FIELD", "numer_rodowodu", "Numer rodowodu"),
                    field(
                        "TEXT_FIELD",
                        "imie_poprzedniego_wlasciciela",
                        "Imię poprzedniego właściciela",
                        True,
                    ),
                    field(
                        "TEXT_FIELD",
                        "nazwisko_poprzedniego_wlasciciela",
                        "Nazwisko poprzedniego właściciela",
                        True,
                    ),
                    field(
                        "TEXT_FIELD",
                        "adres_poprzedniego_wlasciciela",
                        "Adres poprzedniego właściciela",
                        True,
                    ),
                    field("TEXT_FIELD", "rasa_psa", "Rasa psa", True),
                    field("DATEPICKER", "data_urodzenia_psa", "Data urodzenia psa", True),
                    field("DATEPICKER", "data_szczepienia_psa", "Data szczepienia psa"),
                    field("RADIO", "plec_psa", "Płeć psa", True, ["Pies", "Suka"]),
                    field(
                        "RADIO",
                        marking,
                        "Sposób oznakowania psa",
                        True,
                        ["Mikroprocesor", "Tatuaż", "Brak"],
                    ),
                    field(
                        "TEXT_FIELD",
                        "numer_identyfikacyjny_psa",
                        "Numer identyfikacyjny psa",
                        True,
                        when=marked,
                    ),
                    field(
                        "FILE_UPLOADER",
                        "kopia_zaswiadczenia_o_szczepieniu",
                        "Kopia zaświadczenia o szczepieniu przeciwko wściekliźnie",
                        True,
                    ),
                ],
                "Jeśli masz więcej niż jednego psa, dodaj informacje o każdym z nich.",
                repeating=True,
            ),
            address(
                "adres_miejsca_utrzymywania_psow",
                "Adres miejsca utrzymywania psów",
                t2,
                "utrzymywanie_psow",
            ),
            section(
                "warunki_utrzymywania_psow",
                "Warunki utrzymywania psów",
                [
                    field(
                        "TEXTAREA",
                        "opis_miejsca_i_warunkow_utrzymywania",
                        "Opis miejsca i warunków utrzymywania psów",
                        True,
                    )
                ],
            ),
        ],
    )
    fee = section(
        "oplata_skarbowa",
        "Opłata skarbowa za zezwolenie",
        [
            field(
                "TEXT_BLOCK",
                "oplata_skarbowa_info",
                "",
                description="Opłata skarbowa za wydanie zezwolenia wynosi 82 zł. Przelej ją na "
                "konto urzędu: 12 1223 1232 1233 2312 2342 2342. "
                "Dodaj plik z potwierdzeniem przelewu.",
            ),
            field(
                "FILE_UPLOADER",
                "potwierdzenie_oplaty_skarbowej",
                "Plik z potwierdzeniem przelewu",
                True,
            ),
        ],
    )
    statements = [
        ("Oświadczam, że psy nie będą wykorzystywane do polowań.", True),
        ("Oświadczam, że psy są zaszczepione przeciwko wściekliźnie.", True),
        (
            "Oświadczam, że zapewniam warunki utrzymywania psów zgodne z rozporządzeniem "
            "Ministra Rolnictwa i Rozwoju Wsi z dnia 5 lipca 2010 r.",
            True,
        ),
    ]
    return form(
        # K-12: the title stays as in the document, although the content is about greyhounds.
        "Wniosek o wydanie zezwolenia na hodowanie lub utrzymywanie psów ras uznawanych "
        "za agresywne",
        "Urząd Miejski Wrocławia, Wydział Środowiska",
        [K.SELF, K.OTHER_PERSON],
        [dogs],
        contact(statements, fee),
    )


BRACKETS = [
    ("do_45_m2", "do 45 m²"),
    ("od_45_do_60_m2", "powyżej 45 m² do 60 m²"),
    ("od_60_do_80_m2", "powyżej 60 m² do 80 m²"),
    ("powyzej_80_m2", "powyżej 80 m²"),
]


def fee_calculation(
    tech_name: str, title: str, suffix: str, rates: list[int], description: str, when: str
) -> Question:
    """Paper positions 36-51 (or 52-67): count x rate per flat size, minus the income relief."""
    fields = []
    for (key, label), rate in zip(BRACKETS, rates, strict=True):
        fields += [
            field(
                "NUMBER",
                f"liczba_gospodarstw_{key}{suffix}",
                f"Liczba gospodarstw domowych w lokalach {label}",
                description=f"Stawka opłaty: {rate} zł od gospodarstwa domowego.",
            ),
            field(
                "NUMBER",
                f"oplata_{key}{suffix}",
                f"Wysokość miesięcznej opłaty za lokale {label}",
                description=f"Pomnóż liczbę gospodarstw domowych przez {rate} zł.",
            ),
        ]
    fields += [
        field(
            "NUMBER",
            f"liczba_gospodarstw_ze_zwolnieniem{suffix}",
            "Liczba gospodarstw domowych objętych zwolnieniem dochodowym",
            description="Stawka zwolnienia: 15 zł od gospodarstwa domowego.",
        ),
        field(
            "NUMBER",
            f"kwota_zwolnienia{suffix}",
            "Kwota miesięcznego zwolnienia",
            description="Pomnóż liczbę gospodarstw objętych zwolnieniem przez 15 zł.",
        ),
        field(
            "NUMBER",
            f"suma_oplaty{suffix}",
            "Suma miesięcznej opłaty",
            True,
            description="Suma opłat za lokale pomniejszona o kwotę zwolnienia.",
        ),
    ]
    return section(tech_name, title, fields, description, when)


def form_8() -> FormDefinition:
    t2, t3, t4 = "Składający deklarację", "Okoliczności i nieruchomość", "Wysokość opłaty"
    other_entity = "Inny podmiot posiadający nieruchomość w zarządzie lub użytkowaniu"
    joint = "Współwłaściciel (wspólność majątkowa)"
    single = "Nieruchomość zabudowana budynkiem mieszkalnym jednorodzinnym"
    multi = "Nieruchomość zabudowana budynkiem mieszkalnym wielolokalowym"
    submitter = ("skladajacy_deklaracje", "rodzaj_skladajacego")
    property_ = ("dane_nieruchomosci", "rodzaj_nieruchomosci")
    reason = ("okolicznosci_zlozenia_deklaracji", "okolicznosci")
    is_joint = answer_is(joint, t2, *submitter)
    is_single = answer_is(single, t3, *property_)
    is_multi = answer_is(multi, t3, *property_)
    uninhabited = answer_is("Tak", t3, "dane_nieruchomosci", "czesc_niezamieszkala")
    compost = answer_is("Tak", t3, "kompostownik", "czy_nieruchomosc_ma_kompostownik")
    no_compost = answer_is("Nie", t3, "kompostownik", "czy_nieruchomosc_ma_kompostownik")
    fee_rule = (
        "Opłata to suma iloczynów liczby gospodarstw domowych i stawki opłaty ustalonej "
        "uchwałą Rady Miasta Gdyni."
    )

    who = page(
        t2,
        [
            section(
                "skladajacy_deklaracje",
                "Składający deklarację",
                [
                    field(
                        "SELECT",
                        "rodzaj_skladajacego",
                        "Wybierz, kim jesteś jako składający deklarację",
                        True,
                        [
                            "Właściciel lub współwłaściciel",
                            joint,
                            "Najemca lub dzierżawca",
                            "Wspólnota mieszkaniowa",
                            "Spółdzielnia mieszkaniowa",
                            other_entity,
                        ],
                    ),
                    field(
                        "TEXTAREA",
                        "rodzaj_i_dane_innego_podmiotu",
                        "Rodzaj i dane podmiotu",
                        True,
                        description="Podaj, jaki to podmiot, oraz jego dokładne dane.",
                        when=answer_is(other_entity, t2, *submitter),
                    ),
                ],
            ),
            section(
                "dane_wspolmalzonka",
                "Dane współmałżonka",
                [
                    field("TEXT_FIELD", "imie_wspolmalzonka", "Imię", True),
                    field("TEXT_FIELD", "nazwisko_wspolmalzonka", "Nazwisko", True),
                    field("TEXT_FIELD", "numer_pesel_wspolmalzonka", "Numer PESEL", True),
                ],
                when=is_joint,
            ),
            address(
                "adres_zamieszkania_wspolmalzonka",
                "Adres zamieszkania współmałżonka",
                t2,
                "wspolmalzonek",
                is_joint,
            ),
            section(
                "korespondencja",
                "Korespondencja",
                [
                    field(
                        "RADIO",
                        "czy_inny_adres_do_korespondencji",
                        "Czy adres do korespondencji jest inny niż adres zamieszkania "
                        "lub siedziby?",
                        True,
                        YES_NO,
                    )
                ],
            ),
            address(
                "adres_do_korespondencji",
                "Adres do korespondencji",
                t2,
                "korespondencja",
                answer_is("Tak", t2, "korespondencja", "czy_inny_adres_do_korespondencji"),
            ),
        ],
    )
    where = page(
        t3,
        [
            section(
                "okolicznosci_zlozenia_deklaracji",
                "Okoliczności złożenia deklaracji",
                [
                    field(
                        "RADIO",
                        "okolicznosci",
                        "Wybierz, dlaczego składasz deklarację",
                        True,
                        [
                            "Pierwsza deklaracja",
                            "Nowa deklaracja po zmianie danych",
                            "Ustanie obowiązku uiszczania opłaty",
                            "Korekta deklaracji",
                        ],
                    ),
                    field(
                        "DATEPICKER",
                        "data_powstania_obowiazku_oplaty",
                        "Data powstania obowiązku opłaty",
                        True,
                        description="Obowiązek powstaje w dniu, w którym na nieruchomości "
                        "zamieszkał pierwszy mieszkaniec lub powstał pierwszy odpad komunalny.",
                        when=answer_is("Pierwsza deklaracja", t3, *reason),
                    ),
                    field(
                        "DATEPICKER",
                        "data_wystapienia_zmiany_danych",
                        "Data wystąpienia zmiany danych",
                        True,
                        when=any_of(
                            answer_is("Nowa deklaracja po zmianie danych", t3, *reason),
                            answer_is("Korekta deklaracji", t3, *reason),
                        ),
                    ),
                    field(
                        "DATEPICKER",
                        "data_ustania_obowiazku_oplaty",
                        "Data ustania obowiązku opłaty",
                        True,
                        when=answer_is("Ustanie obowiązku uiszczania opłaty", t3, *reason),
                    ),
                ],
            ),
            section(
                "adres_nieruchomosci",
                "Adres nieruchomości",
                [
                    field("TEXT_FIELD", "miejscowosc_nieruchomosci", "Miejscowość", True),
                    field("TEXT_FIELD", "kod_pocztowy_nieruchomosci", "Kod pocztowy", True),
                    field("TEXT_FIELD", "ulica_nieruchomosci", "Ulica"),
                    field("TEXT_FIELD", "numer_budynku_nieruchomosci", "Numer budynku", True),
                    field("TEXT_FIELD", "numer_lokalu_nieruchomosci", "Numer lokalu"),
                ],
                "Złóż osobną deklarację dla każdej nieruchomości.",
            ),
            section(
                "miejsce_gromadzenia_odpadow",
                "Miejsce gromadzenia odpadów",
                [
                    field(
                        "TEXTAREA",
                        "adres_lub_opis_miejsca_pojemnikow",
                        "Adres lub opis miejsca lokalizacji pojemników",
                    ),
                    field(
                        "TEXT_FIELD", "numery_dzialek_geodezyjnych", "Numery działek geodezyjnych"
                    ),
                ],
                "Wypełnij, jeśli składasz deklarację osobno dla części budynku lub dla budynku, "
                "które mają oddzielne miejsce gromadzenia odpadów.",
                when=is_multi,
            ),
            section(
                "dane_nieruchomosci",
                "Dane nieruchomości",
                [
                    field(
                        "RADIO",
                        "rodzaj_nieruchomosci",
                        "Rodzaj nieruchomości",
                        True,
                        [single, multi],
                    ),
                    field(
                        "RADIO",
                        "czesc_niezamieszkala",
                        "Czy na części nieruchomości nie mieszkają mieszkańcy, a powstają na niej "
                        "odpady komunalne?",
                        True,
                        YES_NO,
                        "Jeśli tak, dodasz do deklaracji załącznik A (budynek jednorodzinny) "
                        "lub B (budynek wielolokalowy).",
                    ),
                ],
            ),
            section(
                "kompostownik",
                "Kompostownik",
                [
                    field(
                        "RADIO",
                        "czy_nieruchomosc_ma_kompostownik",
                        "Czy nieruchomość jest wyposażona w przydomowy kompostownik, w którym są "
                        "kompostowane bioodpady?",
                        True,
                        YES_NO,
                        "Właściciele takich nieruchomości są zwolnieni z części opłaty.",
                    )
                ],
                when=is_single,
            ),
        ],
    )
    fee = page(
        t4,
        [
            fee_calculation(
                "oplata_dla_nieruchomosci",
                "Obliczenie wysokości opłaty",
                "",
                [38, 69, 81, 101],
                fee_rule,
                any_of(is_multi, no_compost),
            ),
            fee_calculation(
                "oplata_z_kompostownikiem",
                "Obliczenie wysokości opłaty z kompostownikiem",
                "_kompostownik",
                [28, 59, 71, 91],
                fee_rule + " Stawki są niższe, bo kompostujesz bioodpady w przydomowym "
                "kompostowniku.",
                all_of(is_single, compost),
            ),
            section(
                "oplata_za_czesc_niezamieszkala",
                "Opłata za część nieruchomości, na której nie mieszkają mieszkańcy",
                [
                    field(
                        "NUMBER",
                        "kwota_z_zalacznika",
                        "Kwota opłaty z załącznika A lub B",
                        True,
                        description="Wpisz kwotę z poz. 29 załącznika A lub B do deklaracji.",
                    )
                ],
                when=uninhabited,
            ),
            section(
                "razem_oplata",
                "Razem wysokość miesięcznej opłaty",
                [
                    field(
                        "NUMBER",
                        "razem_wysokosc_miesiecznej_oplaty",
                        "Razem wysokość miesięcznej opłaty",
                        True,
                        description="Suma miesięcznej opłaty z obliczenia powyżej i kwoty "
                        "z załącznika A lub B.",
                    )
                ],
            ),
            section(
                "zalaczniki",
                "Załączniki",
                [
                    field(
                        "FILE_UPLOADER",
                        "zalacznik_a",
                        "Załącznik A do deklaracji",
                        True,
                        when=all_of(uninhabited, is_single),
                    ),
                    field(
                        "FILE_UPLOADER",
                        "zalacznik_b",
                        "Załącznik B do deklaracji",
                        True,
                        when=all_of(uninhabited, is_multi),
                    ),
                    field("FILE_UPLOADER", "inne_zalaczniki", "Inne załączniki"),
                ],
            ),
        ],
    )
    # D.1: the declaration covers only properties in Gdynia, so the town is fixed.
    town = where.questions[1].field.repeating_section_grid[0].field
    assert town.tech_name == "miejscowosc_nieruchomosci"
    town.default_value, town.read_only = "Gdynia", True
    return form(
        "Deklaracja o wysokości miesięcznej opłaty za gospodarowanie odpadami komunalnymi",
        "Prezydent Miasta Gdyni",
        [K.SELF, K.OTHER_PERSON, K.LEGAL_ENTITY],
        [who, where, fee],
        contact(
            [
                (
                    "Wyrażam zgodę na otrzymywanie korespondencji na adres e-mail podany "
                    "w danych do kontaktu.",
                    False,
                )
            ]
        ),
    )


def main() -> None:
    for name, build in (("6", form_6), ("7", form_7), ("8", form_8)):
        golden = build()
        tech_names = [p.field.tech_name for p in _walk(golden)]
        assert len(tech_names) == len(set(tech_names)), f"{name}: duplicate techName"
        issues = check_rules(golden) + check_standards(golden) + check_schema(golden.to_dict())
        assert not [i for i in issues if i.severity is Severity.ERROR], issues
        for issue in issues:
            print(f"{name}: {issue.code} {issue.message}")
        (GOLDEN / f"{name}.json").write_text(golden.to_json() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
