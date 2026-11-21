import json
from pathlib import Path

import pytest

from forms2json.domain.confidence import score
from forms2json.domain.form_definition import (
    Field,
    FlowLink,
    FormDefinition,
    JsonValue,
    Option,
    Question,
    Tab,
)
from forms2json.domain.rules import Severity
from forms2json.domain.standards import (
    SUPPORTED_KEYWORDS,
    check_schema,
    check_standards,
    load_schema,
)

DATA = Path(__file__).parents[3] / "data"
REFERENCES = [
    *DATA.glob("1. */konfiguracja_form_*.json"),
    *DATA.glob("5. */konfiguracja_form_*.json"),
]


def _q(type_: str, tech_name: str, *children: Question, title: str = "") -> Question:
    field = Field(
        id=tech_name,
        type=type_,
        tech_name=tech_name,
        title=title or tech_name.capitalize(),
        question_order=0,
        repeating_section_grid=list(children),
        states=[],
    )
    return Question(x=0, y=0, rows=1, cols=12, field=field)


def _valid_form() -> FormDefinition:
    tabs = [
        Tab(
            "t1",
            "Dane",
            "MAIN",
            [
                _q("SECTION", "urzad_do_ktorego_jest_skladany_wniosek", _q("TEXT_FIELD", "nazwa")),
                _q("SECTION", "twoje_dane", _q("TEXT_FIELD", "imie")),
            ],
        ),
        Tab("t2", "Sprawa", "MAIN", [_q("SECTION", "sprawa", _q("TEXT_FIELD", "cel"))]),
        Tab(
            "t3",
            "Kontakt i zgody",
            "MAIN",
            [
                _q("SECTION", "dane_do_kontaktu", _q("TEXT_FIELD", "numer_telefonu")),
                _q("SECTION", "zgoda", _q("CONSENT_SECTION", "zgoda_pole")),
            ],
        ),
        Tab("t4", "Strona końcowa", "FINISH", [_q("SECTION", "podglad", _q("TEXT_BLOCK", "i"))]),
    ]
    links = [FlowLink(f"l{i}", tabs[i].id, tabs[i + 1].id) for i in range(len(tabs) - 1)]
    return FormDefinition("Wniosek o coś", tabs, links)


def _case_field(form: FormDefinition) -> Field:
    return form.tabs[1].questions[0].field.repeating_section_grid[0].field


def _codes(form: FormDefinition) -> list[str]:
    return [issue.code for issue in check_standards(form)]


def test_valid_form_has_no_issues() -> None:
    assert check_standards(_valid_form()) == []
    assert check_schema(_valid_form().to_dict()) == []


@pytest.mark.parametrize("path", REFERENCES, ids=lambda p: p.parent.name[:2])
def test_reference_has_no_errors(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    issues = check_standards(FormDefinition.from_json(text)) + check_schema(json.loads(text))
    assert [i for i in issues if i.severity is Severity.ERROR] == []
    # The references keep validation: [] everywhere, so missing validators are the only warnings.
    assert {i.code for i in issues} <= {"S-VALIDATOR"}


def test_title_prefix() -> None:
    form = _valid_form()
    form.title = "Prośba o coś"
    assert _codes(form) == ["S-TITLE"]


def test_page_order() -> None:
    form = _valid_form()
    form.tabs[1], form.tabs[2] = form.tabs[2], form.tabs[1]
    issues = check_standards(form)
    assert [(i.code, i.path, i.severity) for i in issues] == [
        ("S-PAGE-ORDER", "tabs[2]", Severity.WARNING)
    ]


def test_missing_predefined_sections() -> None:
    form = _valid_form()
    form.tabs[0].questions = form.tabs[0].questions[1:]
    form.tabs[2].questions = []
    assert _codes(form).count("S-PREDEFINED") == 3


def test_consent_as_checkbox() -> None:
    form = _valid_form()
    _case_field(form).type = "CHECKBOX"
    _case_field(form).title = "Oświadczam, że dane są prawdziwe"
    assert _codes(form) == ["S-CONSENT"]


@pytest.mark.parametrize(
    ("title", "good", "bad"),
    [
        ("Data urodzenia", "DATEPICKER", "TEXT_FIELD"),
        ("Kwota", "NUMBER", "TEXT_FIELD"),
        ("Uzasadnienie", "TEXTAREA", "TEXT_FIELD"),
    ],
)
def test_field_type_matches_label(title: str, good: str, bad: str) -> None:
    form = _valid_form()
    field = _case_field(form)
    field.title = title
    field.type = good
    assert _codes(form) == []
    field.type = bad
    assert _codes(form) == ["S-FIELD-TYPE"]


@pytest.mark.parametrize(
    ("tech_name", "validator"),
    [
        ("adres_e_mail", "EMAIL"),
        ("numer_pesel", "PESEL"),
        ("nip", "NIP"),
        ("regon", "REGON"),
        ("kod_pocztowy", "ZIP_CODE"),
    ],
)
def test_field_needs_validator(tech_name: str, validator: str) -> None:
    form = _valid_form()
    field = _case_field(form)
    field.tech_name = tech_name
    field.validation = ["REQUIRED", validator]
    assert _codes(form) == []
    field.validation = []
    assert _codes(form) == ["S-VALIDATOR"]


def test_foreign_postal_code_needs_no_validator() -> None:
    form = _valid_form()
    _case_field(form).tech_name = "kod_pocztowy_zagranica"
    assert _codes(form) == []


def test_many_options_need_select_with_search() -> None:
    form = _valid_form()
    field = _case_field(form)
    field.type = "RADIO"
    field.options = [Option(str(i), str(i)) for i in range(5)]
    assert _codes(form) == []
    field.options.append(Option("6", "6"))
    assert _codes(form) == ["S-FIELD-TYPE"]
    field.type = "SELECT"
    assert _codes(form) == []
    field.options = [Option(str(i), str(i)) for i in range(16)]
    assert _codes(form) == ["S-FIELD-TYPE"]
    field.search_enabled = True
    assert _codes(form) == []


@pytest.mark.parametrize(
    ("title", "count"),
    [
        ("Numer działki", 0),
        ("KRS", 0),
        ("ulica", 1),
        ("Kod 00-950 Miasto", 1),
        ("ul. Długa 5", 2),
        ("Nazwa ………", 1),
        ("………", 2),
    ],
)
def test_suspicious_label_warns_and_lowers_confidence(title: str, count: int) -> None:
    form = _valid_form()
    _case_field(form).title = title
    issues = check_standards(form)
    assert [i.code for i in issues] == ["S-FIELD-LABEL"] * count
    path = "tabs[1].questions[0].field.repeatingSectionGrid[0].field"
    assert score({path: 0.9}, issues, 0.85).elements[path] == pytest.approx(0.9 - 0.1 * count)


def test_schema_uses_only_supported_keywords() -> None:
    def keywords(node: JsonValue) -> set[str]:
        if not isinstance(node, dict):
            return set()
        # Keys under "properties" are field names, not keywords; descend into their schemas.
        props = node.get("properties", {})
        assert isinstance(props, dict)
        return set(node).union(*map(keywords, [*props.values(), node.get("items")]))

    assert keywords(load_schema()) <= SUPPORTED_KEYWORDS


def test_schema_has_k09_typo_fixed() -> None:
    field_schema = json.dumps(load_schema())
    assert "repeatingSectionGrid" in field_schema
    assert "repetingSectionGrid" not in field_schema


def test_schema_reports_wrong_types() -> None:
    data = _valid_form().to_dict()
    tabs = data["tabs"]
    assert isinstance(tabs, list) and isinstance(tabs[0], dict)
    tabs[0]["title"] = 7
    section = tabs[0]["questions"]
    assert isinstance(section, list) and isinstance(section[0], dict)
    field = section[0]["field"]
    assert isinstance(field, dict)
    field["repeatingSectionGrid"] = {}
    field["readOnly"] = "nie"
    issues = check_schema(data)
    assert [(i.path, i.severity) for i in issues] == [
        ("tabs[0].title", Severity.ERROR),
        ("tabs[0].questions[0].field.readOnly", Severity.ERROR),
        ("tabs[0].questions[0].field.repeatingSectionGrid", Severity.ERROR),
    ]
    assert check_schema([]) != []
