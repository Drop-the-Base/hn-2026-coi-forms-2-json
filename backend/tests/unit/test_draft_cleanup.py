import pytest

from forms2json.domain.draft_cleanup import SUBJECT_FALLBACK, clean_draft, sentence_case
from forms2json.domain.form_draft import ApplicantKind
from tests.unit.test_compose_step import _draft, _field


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("WNIOSEK O WYDANIE KARTY", "Wniosek o wydanie karty"),
        ("WNIOSEK o wydanie karty", "Wniosek o wydanie karty"),
        ("Wniosek do Rady Miasta Gdańska", "Wniosek do Rady Miasta Gdańska"),
        ("NIP", "NIP"),
        ("Numer PESEL", "Numer PESEL"),
        ("ulica", "ulica"),
    ],
)
def test_sentence_case(text: str, expected: str) -> None:
    assert sentence_case(text) == expected


def test_drops_addressee_paper_and_applicant_fields() -> None:
    draft = _draft(
        "WNIOSEK O WYDANIE KARTY",
        "Starosta Powiatu Leśnego",
        [
            _field("data", "(data)", "Strona 1", "DATEPICKER"),
            _field("kto", "imię i nazwisko/nazwa wnioskodawcy", "Strona 1"),
            _field("adres", "adres", "Strona 1"),
            _field("kontakt", "nr telefonu/adres e-mail", "Strona 1"),
            _field("organ", "Starosta Powiatu Leśnego", "Strona 1"),
            _field("organ_adres", "Starosta Powiatu Leśnego, ul. Polna 1", "Strona 1"),
            _field("pesel", "PESEL", "Dane wnioskodawcy"),
            _field("nip", "NIP", "Informacje ogólne"),
            _field("firma", "Nazwisko i imię/Nazwa firmy", "Informacje ogólne"),
            _field("data_w", "Data wniosku", "Informacje ogólne", "DATEPICKER"),
            _field("karta", "Rodzaj karty", "Strona 2"),
            _field("powod", "Powód", "DANE KARTY"),
            _field("podpis", "podpis wnioskodawcy", "Strona 2"),
            _field("miejsce_data", "Miejscowość i data", "Strona 2"),
            _field("zal", "Załączniki", "Strona 2", "CHECKBOX"),
        ],
        applicants=[{"kind": "SELF", "confidence": 1.0}],
        conditions=[{"target": "karta", "source": "data", "value": "x", "confidence": 1.0}],
    )
    clean = clean_draft(draft)
    assert clean.title.value == "Wniosek o wydanie karty"
    assert [(f.key, f.section) for f in clean.fields] == [
        ("karta", SUBJECT_FALLBACK),
        ("powod", "Dane karty"),
    ]
    assert clean.conditions == []  # its source was dropped
    # "nazwa wnioskodawcy" means a company may apply; a proxy is always possible.
    assert {a.kind for a in clean.applicants} == {
        ApplicantKind.SELF,
        ApplicantKind.PROXY,
        ApplicantKind.LEGAL_ENTITY,
    }


def test_keeps_subject_fields_that_only_resemble_noise() -> None:
    fields = [
        _field("data_ur", "Data urodzenia", "Dane dziecka", "DATEPICKER"),
        _field("miejsce", "Miejscowość", "Dane dziecka"),
        _field("adres_n", "Adres nieruchomości", "Dane dziecka"),
        _field("gmina", "Gmina", "Dane dziecka"),
        _field("imie", "Imię", "Osoba odpowiedzialna za porządek"),
    ]
    clean = clean_draft(_draft("Wniosek o coś", "Wójt Gminy Leśna", fields))
    assert [f.key for f in clean.fields] == ["data_ur", "miejsce", "adres_n", "gmina", "imie"]


def test_drops_what_standard_blocks_cover_and_paper_positions() -> None:
    consent = "Wyrażam zgodę na korespondencję e-mail"
    draft = _draft(
        "Deklaracja",
        "Prezydent Miasta",
        [
            _field("nazwa", "Nazwa pełna / imię i nazwisko", "Dane podmiotu"),
            _field("nip", "NIP / REGON (dot. tylko osób prawnych)", "Dane podmiotu"),
            _field("tel", "Nr tel./fax", "Dane kontaktowe"),
            _field("mail", "Adres e‑mail", "Dane kontaktowe"),  # noqa: RUF001 - models write U+2011
            _field("zgoda", consent[:30], "Dane kontaktowe", "CHECKBOX"),
            _field("suma", "Suma opłat (suma poz. 38, 41 i 44)", "Obliczenia", "NUMBER"),
            _field("zal_a", "Załącznik A", "Kontakt i załączniki", "RADIO", options=["TAK", "NIE"]),
            _field("inne", "Inne załączniki (podać jakie)", "Załączniki"),
            _field("pelnomocnictwo", "Pełnomocnictwo", "Załączniki", "CHECKBOX"),
        ],
        attachments=[{"name": "Inne (podać jakie)", "required": False, "confidence": 0.9}],
        fees=[
            {"description": "Opłata skarbowa za pełnomocnictwo", "amount": 17.0, "confidence": 0.9}
        ],
        consents=[{"text": consent, "required": False, "confidence": 0.9}],
    )

    cleaned = clean_draft(draft)

    assert [f.label for f in cleaned.fields] == ["Suma opłat"]
    assert [a.name for a in cleaned.attachments] == ["Inne (podać jakie)", "Załącznik A"]
    assert cleaned.fees == []


def test_correspondence_address_gets_a_yes_no_gate() -> None:
    draft = _draft(
        "Deklaracja",
        "Prezydent Miasta",
        [_field("korespondencja", "Adres do korespondencji", "Adresy", "ADDRESS")],
    )

    cleaned = clean_draft(draft)

    gate, address = cleaned.fields
    assert (gate.type, gate.options, gate.section) == ("RADIO", ["Tak", "Nie"], "Adresy")
    assert [(c.target, c.source, c.value) for c in cleaned.conditions] == [
        ("korespondencja", gate.key, "Tak")
    ]
    assert address.key == "korespondencja"


def test_address_parts_become_one_address_field() -> None:
    parts = ["Kraj", "Miejscowość", "Ulica", "Numer domu", "Kod pocztowy"]
    draft = _draft(
        "Deklaracja",
        "Prezydent Miasta",
        [
            *(_field(f"n{i}", p, "Adres nieruchomości", "TEXT_FIELD") for i, p in enumerate(parts)),
            _field("dzialka", "Numer działki", "Adres nieruchomości", "TEXT_FIELD"),
        ],
    )

    cleaned = clean_draft(draft)

    assert [(f.key, f.label, f.type) for f in cleaned.fields] == [
        ("nieruchomosci", "Adres nieruchomości", "ADDRESS"),
        ("dzialka", "Numer działki", "TEXT_FIELD"),
    ]


def test_address_part_next_to_an_address_field_is_dropped() -> None:
    draft = _draft(
        "Deklaracja",
        "Prezydent Miasta",
        [
            _field("nieruchomosc", "Adres nieruchomości", "Nieruchomość", "ADDRESS"),
            _field("nr", "Numer nieruchomości / domu", "Nieruchomość", "TEXT_FIELD"),
            _field("miejscowosc", "Miejscowość", "Inne", "TEXT_FIELD"),
        ],
    )

    assert [f.key for f in clean_draft(draft).fields] == ["nieruchomosc", "miejscowosc"]
