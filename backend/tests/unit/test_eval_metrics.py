from forms2json.domain.form_definition import Field, FlowLink, FormDefinition, Question, State, Tab
from tests.evals.metrics import Scores, score, to_markdown


def _q(type_: str, tech_name: str, *children: Question, query: str = "") -> Question:
    field = Field(
        id=tech_name,
        type=type_,
        tech_name=tech_name,
        title=tech_name,
        question_order=0,
        repeating_section_grid=list(children),
        states=[State("SHOW", query)] if query else [],
    )
    return Question(x=0, y=0, rows=1, cols=12, field=field)


def _form(*sections: Question) -> FormDefinition:
    finish = Tab("t2", "Koniec", "FINISH", [_q("SECTION", "podglad", _q("TEXT_BLOCK", "info"))])
    return FormDefinition(
        "Wniosek", [Tab("t1", "Dane", "MAIN", list(sections)), finish], [FlowLink("l", "t1", "t2")]
    )


GOLDEN = _form(
    _q("SECTION", "dane", _q("TEXT_FIELD", "imie"), _q("RADIO", "kto")),
    _q("SECTION", "adres", _q("TEXT_FIELD", "ulica", query="'Polska' in x"), query="a"),
)


def test_identical_forms_score_perfectly() -> None:
    assert score(GOLDEN, GOLDEN) == Scores(0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)


def test_missing_section_and_extra_field_lower_recall_and_precision() -> None:
    predicted = _form(
        _q("SECTION", "dane", _q("TEXT_FIELD", "imie"), _q("RADIO", "kto"), _q("DATE", "data"))
    )
    s = score(predicted, GOLDEN)
    assert (s.section_precision, s.section_recall) == (1.0, 2 / 3)
    assert (s.field_precision, s.field_recall) == (3 / 4, 3 / 4)


def test_wrong_type_lowers_type_accuracy() -> None:
    predicted = _form(
        _q("SECTION", "dane", _q("TEXT_FIELD", "imie"), _q("SELECT", "kto")),
        _q("SECTION", "adres", _q("TEXT_FIELD", "ulica", query="'Polska' in x"), query="a"),
    )
    assert score(predicted, GOLDEN).type_accuracy == 3 / 4


def test_conditions_compare_ignoring_whitespace() -> None:
    predicted = _form(
        _q("SECTION", "dane", _q("TEXT_FIELD", "imie"), _q("RADIO", "kto", query="b")),
        _q("SECTION", "adres", _q("TEXT_FIELD", "ulica", query="'Polska'\r\n in  x"), query="a"),
    )
    # adres and ulica match; kto has a condition the golden lacks.
    assert score(predicted, GOLDEN).condition_accuracy == 2 / 3


def test_rule_errors_count_violations_of_the_prediction() -> None:
    predicted = _form(_q("TEXT_FIELD", "poza_sekcja"))
    assert score(predicted, GOLDEN).rule_errors == 1


def test_markdown_table_has_a_row_per_case() -> None:
    table = to_markdown({"a": score(GOLDEN, GOLDEN)})
    assert table.splitlines()[-1] == "| a | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |"


def test_f1_is_the_harmonic_mean_and_zero_without_hits() -> None:
    s = Scores(0, 1.0, 0.5, 0.0, 0.0, 1.0, 1.0)
    assert s.section_f1 == 2 / 3
    assert s.field_f1 == 0.0
