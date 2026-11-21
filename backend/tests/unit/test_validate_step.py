from pathlib import Path

from forms2json.application.pipeline.validate_step import ValidateStep
from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.rules import Severity

DATA = Path(__file__).parents[3] / "data"


def test_reference_form_has_no_errors() -> None:
    (path,) = DATA.glob("1. */konfiguracja_form_*.json")
    form = FormDefinition.from_json(path.read_text(encoding="utf-8"))

    result = ValidateStep().run(form)

    assert result.form is form
    assert [i for i in result.issues if i.severity is Severity.ERROR] == []


def test_broken_form_gets_rule_and_standard_issues() -> None:
    result = ValidateStep().run(FormDefinition(title=""))

    codes = {issue.code for issue in result.issues}
    assert any(code.startswith("R-") for code in codes)
    assert any(code.startswith("S-") for code in codes)
