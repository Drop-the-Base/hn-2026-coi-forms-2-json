import json
import re
from pathlib import Path

import pytest

from forms2json.domain.form_definition import State
from forms2json.domain.jsonata import (
    all_of,
    answer_is,
    answer_is_not,
    any_of,
    read_only,
    show,
)
from forms2json.domain.rules import TAB_TITLE_REF, TECH_NAME_REF

DATA = Path(__file__).parents[3] / "data"
REFERENCES = [
    *DATA.glob("1. */konfiguracja_form_*.json"),
    *DATA.glob("5. */konfiguracja_form_*.json"),
]

APPLICANT = ("Dane", "podmiot_wniosku", "wybierz_w_czyim_imieniu_wnioskujesz")
ROLE = ("Dane", "podmiot_wniosku", "wybierz_jako_kto_wnioskujesz")
LEGAL = answer_is("Osoby prawnej lub jednostki organizacyjnej", *APPLICANT)
OTHER = answer_is("Innej osoby", *APPLICANT)

GENERATED = [
    LEGAL,
    OTHER,
    *(
        build("Polska", "Dane", section, field)
        for build in (answer_is, answer_is_not)
        for section, field in [
            ("adres_zamieszkania", "kraj"),
            ("adres_siedziby", "kraj_siedziba"),
            ("adres_zamieszkania_osoby_ktorej_jestes_pelnomocnikiem", "kraj_inna_osoba"),
        ]
    ),
    answer_is(
        "Tak",
        "Dane",
        "oplata_skarbowa_pelnomocnictwo_1",
        "czy_zlozenie_pelnomocnictwa_wymaga_oplaty_skarbowej",
    ),
    *(
        answer_is(
            value,
            "Informacje o nadpłacie",
            "rozliczenie_nadplaty",
            "wybierz_co_mamy_zrobic_z_nadplata",
        )
        for value in [
            "Zaliczyć na poczet przyszłego zobowiązania podatkowego",
            "Zwrócić przelewem na rachunek bankowy",
        ]
    ),
    all_of(LEGAL, answer_is("Reprezentant", *ROLE)),
    all_of(LEGAL, answer_is("Pełnomocnik", *ROLE)),
    any_of(OTHER, all_of(LEGAL, answer_is("Pełnomocnik", *ROLE))),
]


def _reference_queries() -> set[str]:
    queries: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            queries.update(s["query"] for s in node.get("states") or [])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in REFERENCES:
        walk(json.loads(path.read_text(encoding="utf-8")))
    return queries


def _normalize(query: str) -> str:
    """References put arbitrary CRLFs around `and` / `or`; the whitespace has no meaning."""
    return re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", re.sub(r"\s+", " ", query))).strip()


def test_generated_queries_cover_exactly_the_references() -> None:
    assert len(REFERENCES) == 2
    assert {_normalize(q) for q in GENERATED} == {_normalize(q) for q in _reference_queries()}


@pytest.mark.parametrize("query", [q for q in GENERATED if " and " not in q])
def test_single_conditions_match_references_byte_for_byte(query: str) -> None:
    # Some reference queries end with a stray CRLF.
    assert query in {q.rstrip() for q in _reference_queries()}


def test_values_from_llm_are_escaped() -> None:
    query = answer_is('Opcja "A" \\ b\n', "Strona 'X'", "sekcja", "pole")

    assert query.startswith('("Opcja \\"A\\" \\\\ b\\n" in ')
    assert "tabs['Strona \\u0027X\\u0027' in title]" in query
    # Rules parse references from the query; escaping must not break that.
    assert TAB_TITLE_REF.findall(query) == ["Strona \\u0027X\\u0027"]
    assert TECH_NAME_REF.findall(query) == ["sekcja", "pole"]


def test_all_of_wraps_an_or_operand() -> None:
    assert all_of("a or b", "c") == "(a or b) and c"


def test_states() -> None:
    assert show("q") == State("SHOW", "q")
    assert read_only("q") == State("READ_ONLY", "q")
