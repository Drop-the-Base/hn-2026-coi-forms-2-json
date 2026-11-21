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
