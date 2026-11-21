from itertools import pairwise
from pathlib import Path

import pytest

from forms2json.domain.blocks.pages import applicant_page, contact_page, finish_page
from forms2json.domain.form_definition import Field, FlowLink, FormDefinition, Question, Tab
from forms2json.domain.form_draft import ApplicantKind, Consent
from forms2json.domain.rules import check_rules

DATA = Path(__file__).parents[3] / "data"
REFERENCE_1 = next(DATA.glob("1. */konfiguracja_form_*.json"))
REFERENCE_5 = next(DATA.glob("5. */konfiguracja_form_*.json"))
ALL_KINDS = [ApplicantKind.SELF, ApplicantKind.OTHER_PERSON, ApplicantKind.LEGAL_ENTITY]
# Reference 1 names these differently; the blocks follow reference 5, which matches the Standardy.
RENAMES_1 = {
    "dokument_z_potwierdzeniem_podpisany_elektronicznie": "plik_dokumentu_z_pelnomocnictwem",
    "potwierdzenie_przelewu": "plik_z_potwierdzeniem_przelewu",
    "potwierdzenie_przelewu_2": "plik_z_potwierdzeniem_przelewu_2",
    "zgoda_sekcja": "zgoda_wyrazenie",
}

type Shape = tuple[str, str, list[str]]


def _shape(field: Field, renames: dict[str, str]) -> Shape:
    """What a block must reproduce: techName, type and SHOW conditions (whitespace ignored)."""
    queries = ["".join(s.query.split()) for s in field.states or []]
    return renames.get(field.tech_name, field.tech_name), field.type, queries


def _sections(tab: Tab) -> list[Question]:
    return sorted(tab.questions, key=lambda q: q.y)


@pytest.mark.parametrize(
    ("path", "renames"), [(REFERENCE_1, RENAMES_1), (REFERENCE_5, {})], ids=["1", "5"]
)
def test_blocks_cover_reference_pages(path: Path, renames: dict[str, str]) -> None:
    reference = FormDefinition.from_json(path.read_text(encoding="utf-8"))
    addressee = reference.tabs[0].questions[0].field.repeating_section_grid[0].field
    assert isinstance(addressee.default_value, str)
    built = [applicant_page(addressee.default_value, ALL_KINDS), contact_page(), finish_page()]

    for expected_tab, tab in zip(
        [reference.tabs[0], reference.tabs[-2], reference.tabs[-1]], built, strict=True
    ):
        expected_sections = _sections(expected_tab)
        sections = _sections(tab)
        assert [_shape(q.field, renames) for q in expected_sections] == [
            _shape(q.field, {}) for q in sections
        ]
        for expected, section in zip(expected_sections, sections, strict=True):
            children = [_shape(c.field, {}) for c in section.field.repeating_section_grid]
            # Blocks may add fields the Standardy require (REGON, KRS, PESEL of another person).
            for child in expected.field.repeating_section_grid:
                assert _shape(child.field, renames) in children


@pytest.mark.parametrize(
    "kinds",
    [
        [],
        [ApplicantKind.SELF],
        [ApplicantKind.SELF, ApplicantKind.PROXY],
        [ApplicantKind.LEGAL_ENTITY],
        ALL_KINDS,
    ],
    ids=str,
)
def test_form_built_from_blocks_passes_rules(kinds: list[ApplicantKind]) -> None:
    subject = Field("s", "SECTION", "sprawa", "Sprawa", 0, states=[])
    subject.repeating_section_grid = [
        Question(0, 0, 1, 3, Field("f", "TEXT_FIELD", "opis", "Opis", 0, states=[]))
    ]
    tabs = [
        applicant_page("Urząd Gminy Testowo", kinds),
        Tab("subject", "Sprawa", "MAIN", [Question(0, 0, 2, 3, subject)]),
        contact_page(),
        finish_page(),
    ]
    links = [FlowLink(f"l{i}", a.id, b.id) for i, (a, b) in enumerate(pairwise(tabs))]

    assert check_rules(FormDefinition("Wniosek testowy", tabs, links)) == []


def test_only_self_skips_subject_section() -> None:
    names = [q.field.tech_name for q in applicant_page("Urząd", [ApplicantKind.SELF]).questions]

    assert names == ["urzad_do_ktorego_jest_skladany_wniosek", "twoje_dane", "adres_zamieszkania"]


def test_each_build_gets_fresh_ids() -> None:
    def ids() -> list[str]:
        tab = applicant_page("Urząd", ALL_KINDS)
        return [tab.id] + [
            f.id
            for q in tab.questions
            for f in [q.field, *(c.field for c in q.field.repeating_section_grid)]
        ]

    first, second = ids(), ids()

    assert len(set(first)) == len(first)
    assert not set(first) & set(second)


def test_draft_consents_keep_required_and_escape_text() -> None:
    tab = contact_page(
        [
            Consent(text="Oświadczam <to>", required=True, confidence=0.9),
            Consent(text="Zgoda", required=False, confidence=0.8),
        ]
    )

    consent_section = tab.questions[1].field
    config = consent_section.repeating_section_grid[0].field.consent_section_config
    assert consent_section.title == "Zgody i oświadczenia"
    assert config is not None
    assert config["consents"] == [
        {
            "description": "<html><head></head><body><p>Oświadczam &lt;to&gt;</p></body></html>",
            "required": True,
        },
        {"description": "<html><head></head><body><p>Zgoda</p></body></html>", "required": False},
    ]


def test_changing_a_block_does_not_leak_into_the_next_one() -> None:
    first = contact_page().questions[1].field.repeating_section_grid[0].field
    assert first.consent_section_config is not None
    first.consent_section_config["consents"].append({"description": "x", "required": True})  # type: ignore[union-attr]
    second = contact_page().questions[1].field.repeating_section_grid[0].field
    assert second.consent_section_config is not None
    assert len(second.consent_section_config["consents"]) == 1  # type: ignore[arg-type]
