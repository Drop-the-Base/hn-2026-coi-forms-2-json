import pytest

from forms2json.domain.draft_cleanup import (
    INFERRED_CONFIDENCE,
    SUBJECT_FALLBACK,
    clean_draft,
    sentence_case,
)
from forms2json.domain.form_definition import JsonObject, JsonValue
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


CHOICE = "Wybierz rodzaj prac"
WORKS = [
    _field("rodzaj", CHOICE, "Prace", "RADIO", options=["Remont", "Budowa"]),
    _field("opis", "Opis prac", "Prace", "TEXTAREA"),
    _field("opis", "Opis prac dodatkowych", "Prace", "TEXTAREA"),
]
PLAN: JsonObject = {"key": "plan", "name": "Plan prac", "required": True, "confidence": 0.9}


def _when(target: str, source: str = "rodzaj") -> JsonValue:
    return {"target": target, "source": source, "value": "Budowa", "confidence": 0.9}


def test_dangling_condition_is_dropped_and_its_target_flagged() -> None:
    conditions = [_when("opis", source="brak"), _when("nie_ma"), _when("plan")]
    clean = clean_draft(
        _draft("Wniosek", "Urząd", WORKS, conditions=conditions, attachments=[PLAN])
    )

    assert [c.target for c in clean.conditions] == ["plan"]  # an attachment is a valid target
    assert [(f.key, f.confidence) for f in clean.fields] == [
        ("rodzaj", 0.9),
        ("opis", INFERRED_CONFIDENCE),  # always shown now: review it
        ("opis_2", 0.9),
    ]


def test_repeated_keys_get_a_suffix_across_fields_and_attachments() -> None:
    attachments: JsonValue = [PLAN, PLAN | {"key": "opis"}]
    clean = clean_draft(_draft("Wniosek", "Urząd", WORKS, attachments=attachments))

    assert [f.key for f in clean.fields] == ["rodzaj", "opis", "opis_2"]
    assert [a.key for a in clean.attachments] == ["plan", "opis_3"]


def test_address_or_person_is_no_condition_source() -> None:
    fields = [*WORKS, _field("inwestor", "Imię i nazwisko inwestora", "Prace", "PERSON")]
    clean = clean_draft(_draft("W", "U", fields, conditions=[_when("opis", source="inwestor")]))

    assert clean.conditions == []
