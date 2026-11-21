import copy
from pathlib import Path

import pytest

from forms2json.domain.blocks.pages import applicant_page, contact_page, finish_page
from forms2json.domain.form_definition import FormDefinition, Question, Tab
from forms2json.domain.form_draft import ApplicantKind
from forms2json.domain.layout import TechNames, layout_page, slugify

DATA = Path(__file__).parents[3] / "data"
REFERENCES = [next(DATA.glob(f"{n}. */konfiguracja_form_*.json")) for n in (1, 5)]
# References give these 9-field sections 9 or 8 rows (no header row, or overflow); we use 10.
ADDRESS_SECTIONS = {
    "adres_zamieszkania",
    "adres_siedziby",
    "adres_zamieszkania_osoby_ktorej_jestes_pelnomocnikiem",
}

type Box = tuple[int, int, int, int]


def _box(q: Question) -> Box:
    return q.x, q.y, q.rows, q.cols


def _relaid(tab: Tab) -> list[Question]:
    """The reference tab's sections in reading order, laid out again by our code."""
    sections = sorted(copy.deepcopy(tab.questions), key=lambda q: q.y)
    for section in sections:
        section.field.repeating_section_grid.sort(key=lambda q: q.y)
    layout_page(sections)
    return sections


def _reference_tabs() -> list[Tab]:
    return [
        tab
        for path in REFERENCES
        for tab in FormDefinition.from_json(path.read_text(encoding="utf-8")).tabs
    ]


def _assert_no_overlap(boxes: list[Box]) -> None:
    cells = [
        (x, y)
        for bx, by, rows, cols in boxes
        for x in range(bx, bx + cols)
        for y in range(by, by + rows)
    ]
    assert len(cells) == len(set(cells))


@pytest.mark.parametrize("tab", _reference_tabs(), ids=lambda t: t.title)
def test_layout_matches_references_for_fields(tab: Tab) -> None:
    reference = sorted(tab.questions, key=lambda q: q.y)
    for expected, section in zip(reference, _relaid(tab), strict=True):
        expected_children = sorted(expected.field.repeating_section_grid, key=lambda q: q.y)
        assert [(_box(c), c.field.question_order) for c in expected_children] == [
            (_box(c), c.field.question_order) for c in section.field.repeating_section_grid
        ]


@pytest.mark.parametrize(
    "tab",
    [
        t
        for t in _reference_tabs()
        if not ADDRESS_SECTIONS & {q.field.tech_name for q in t.questions}
    ],
    ids=lambda t: t.title,
)
def test_layout_matches_references_for_sections(tab: Tab) -> None:
    reference = sorted(tab.questions, key=lambda q: q.y)

    assert [(_box(q), q.field.question_order) for q in reference] == [
        (_box(q), q.field.question_order) for q in _relaid(tab)
    ]


@pytest.mark.parametrize("tab", _reference_tabs(), ids=lambda t: t.title)
def test_layout_has_no_collisions(tab: Tab) -> None:
    sections = _relaid(tab)

    _assert_no_overlap([_box(s) for s in sections])
    for s in sections:
        children = [_box(c) for c in s.field.repeating_section_grid]
        _assert_no_overlap(children)
        # Fields fit below the section's header row.
        assert all(y + rows < s.rows for _, y, rows, _ in children)


def test_question_order_follows_given_order() -> None:
    tab = applicant_page("Urząd", [ApplicantKind.SELF, ApplicantKind.LEGAL_ENTITY])

    orders = [q.field.question_order for q in tab.questions]
    assert orders == sorted(orders) == [q.y for q in tab.questions]


@pytest.mark.parametrize(
    ("label", "slug"),
    [
        ("Organ, do którego jest składany wniosek", "organ_do_ktorego_jest_skladany_wniosek"),
        ("Adres e-mail", "adres_e_mail"),
        ("ŻÓŁĆ gęślą jaźń", "zolc_gesla_jazn"),
        (
            "Czy złożenie pełnomocnictwa wymaga opłaty skarbowej?",
            "czy_zlozenie_pelnomocnictwa_wymaga_oplaty_skarbowej",
        ),
        ("  Numer KRS  ", "numer_krs"),
    ],
)
def test_slugify_polish_labels(label: str, slug: str) -> None:
    assert slugify(label) == slug


def test_tech_names_are_unique_in_form() -> None:
    blocks = [applicant_page("Urząd", [ApplicantKind.SELF]), contact_page(), finish_page()]
    taken = [
        f.tech_name
        for tab in blocks
        for q in tab.questions
        for f in [q.field, *(c.field for c in q.field.repeating_section_grid)]
    ]
    names = TechNames(taken)

    new = [names.new(label) for label in ["Ulica", "Ulica", "Uwagi", "", "", "?"]]

    assert new == ["ulica_2", "ulica_3", "uwagi", "pole", "pole_2", "pole_3"]
    assert len(set(taken + new)) == len(taken) + len(new)
