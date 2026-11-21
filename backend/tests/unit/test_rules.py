from pathlib import Path

import pytest

from forms2json.domain.form_definition import (
    Field,
    FlowLink,
    FormDefinition,
    JsonObject,
    Question,
    State,
    Tab,
)
from forms2json.domain.rules import Severity, check_rules

DATA = Path(__file__).parents[3] / "data"
REFERENCES = [
    *DATA.glob("1. */konfiguracja_form_*.json"),
    *DATA.glob("5. */konfiguracja_form_*.json"),
]


def _q(
    type_: str, tech_name: str, *children: Question, consents: JsonObject | None = None
) -> Question:
    field = Field(
        id=tech_name,
        type=type_,
        tech_name=tech_name,
        title=tech_name,
        question_order=0,
        repeating_section_grid=list(children),
        states=[],
        consent_section_config=consents,
    )
    return Question(x=0, y=0, rows=1, cols=12, field=field)


def _valid_form() -> FormDefinition:
    main = Tab("t1", "Dane", "MAIN", [_q("SECTION", "dane", _q("TEXT_FIELD", "imie"))])
    finish = Tab(
        "t2", "Strona końcowa", "FINISH", [_q("SECTION", "podglad", _q("TEXT_BLOCK", "info"))]
    )
    return FormDefinition("Wniosek", [main, finish], [FlowLink("l1", "t1", "t2")])


def _codes(form: FormDefinition) -> list[str]:
    return [issue.code for issue in check_rules(form)]


def _field(form: FormDefinition, tab: int = 0) -> Field:
    """The first field inside the first section of the given tab."""
    return form.tabs[tab].questions[0].field.repeating_section_grid[0].field


def test_valid_form_has_no_issues() -> None:
    assert check_rules(_valid_form()) == []


@pytest.mark.parametrize("path", REFERENCES, ids=lambda p: p.parent.name[:2])
def test_reference_passes(path: Path) -> None:
    # Known reference inconsistencies (analiza §5) are invisible here: "validation": {} is read
    # as [] by the model (K-05) and TEXT_BLOCK on FINISH is accepted (K-07).
    assert check_rules(FormDefinition.from_json(path.read_text(encoding="utf-8"))) == []


def test_title_longer_than_255_fails() -> None:
    form = _valid_form()
    form.title = "x" * 255
    assert _codes(form) == []
    form.title = "x" * 256
    assert _codes(form) == ["R-TITLE"]


def test_empty_title_fails() -> None:
    form = _valid_form()
    form.title = " "
    assert _codes(form) == ["R-TITLE"]


def test_single_tab_fails() -> None:
    form = _valid_form()
    form.tabs = form.tabs[1:]
    form.links = []
    assert "R-TAB-COUNT" in _codes(form)


def test_last_tab_not_finish_fails() -> None:
    form = _valid_form()
    form.tabs[1].type = "MAIN"
    assert _codes(form) == ["R-TAB-TYPE"]


def test_finish_before_last_tab_fails() -> None:
    form = _valid_form()
    form.tabs[0].type = "FINISH"
    # Its TEXT_FIELD also becomes an input on a FINISH page.
    assert _codes(form) == ["R-TAB-TYPE", "R-FINISH-INPUT"]


def test_tab_with_only_empty_section_fails() -> None:
    form = _valid_form()
    form.tabs[0].questions = [_q("SECTION", "pusta")]
    assert _codes(form) == ["R-TAB-EMPTY"]


def test_field_outside_section_fails() -> None:
    form = _valid_form()
    form.tabs[0].questions.append(_q("TEXT_FIELD", "luzem"))
    assert _codes(form) == ["R-FIELD-OUTSIDE-SECTION"]


def test_field_inside_non_section_fails() -> None:
    form = _valid_form()
    _field(form).repeating_section_grid = [_q("TEXT_FIELD", "dziecko")]
    assert _codes(form) == ["R-FIELD-OUTSIDE-SECTION"]


def test_field_in_repeating_section_passes() -> None:
    form = _valid_form()
    form.tabs[0].questions.append(_q("REPEATING_SECTION", "osoby", _q("TEXT_FIELD", "nazwisko")))
    assert _codes(form) == []


def test_section_in_section_fails() -> None:
    form = _valid_form()
    form.tabs[0].questions[0].field.repeating_section_grid.append(
        _q("REPEATING_SECTION", "wewnetrzna", _q("TEXT_FIELD", "pole"))
    )
    assert _codes(form) == ["R-SECTION-NESTED"]


def test_input_on_finish_fails() -> None:
    form = _valid_form()
    _field(form, tab=1).type = "TEXT_FIELD"
    assert _codes(form) == ["R-FINISH-INPUT"]


@pytest.mark.parametrize(
    "questions",
    [
        [_q("INFO_SECTION", "info")],
        [_q("SECTION", "podglad", _q("INFO_SECTION", "info"))],
    ],
    ids=["info-section-on-page", "info-section-in-section"],
)
def test_info_section_on_finish_passes(questions: list[Question]) -> None:
    form = _valid_form()
    form.tabs[1].questions = questions
    assert _codes(form) == []


def test_known_validators_pass() -> None:
    form = _valid_form()
    _field(form).validation = ["REQUIRED", "PESEL"]
    assert _codes(form) == []


def test_unknown_validator_fails() -> None:
    form = _valid_form()
    _field(form).validation = ["REQUIRED", "WYMAGANE"]
    assert _codes(form) == ["R-OBLIGATORY"]


def test_consent_with_required_passes() -> None:
    form = _valid_form()
    consent = _q("CONSENT_SECTION", "zgody", consents={"consents": [{"required": True}]})
    form.tabs[0].questions[0].field.repeating_section_grid.append(consent)
    assert _codes(form) == []


def test_consent_without_required_fails() -> None:
    form = _valid_form()
    consent = _q("CONSENT_SECTION", "zgody", consents={"consents": [{"description": "x"}]})
    form.tabs[0].questions[0].field.repeating_section_grid.append(consent)
    assert _codes(form) == ["R-OBLIGATORY"]


def test_missing_flow_link_fails() -> None:
    form = _valid_form()
    form.links = []
    assert _codes(form) == ["R-FLOW"]


def test_flow_link_to_unknown_tab_fails() -> None:
    form = _valid_form()
    form.links.append(FlowLink("l2", "t2", "nieznana"))
    assert _codes(form) == ["R-FLOW"]


def test_valid_states_pass() -> None:
    form = _valid_form()
    query = (
        "\"Tak\" in tabs['Dane' in title].questions['dane' in field.techName].field.__userAnswer"
    )
    _field(form).states = [State("SHOW", query), State("READ_ONLY", query)]
    assert _codes(form) == []


def test_read_only_state_on_section_fails() -> None:
    form = _valid_form()
    form.tabs[0].questions[0].field.states = [State("READ_ONLY", "true")]
    assert _codes(form) == ["R-STATES"]


def test_state_without_query_fails() -> None:
    form = _valid_form()
    _field(form).states = [State("SHOW", "")]
    assert _codes(form) == ["R-STATES"]


def test_state_referencing_unknown_field_warns() -> None:
    form = _valid_form()
    query = (
        "\"Tak\" in tabs['Inna' in title].questions['brak' in field.techName].field.__userAnswer"
    )
    _field(form).states = [State("SHOW", query)]
    issues = check_rules(form)
    assert [(i.code, i.severity) for i in issues] == [("R-STATES", Severity.WARNING)] * 2
    assert issues[0].path == "tabs[0].questions[0].field.repeatingSectionGrid[0].field.states[0]"
