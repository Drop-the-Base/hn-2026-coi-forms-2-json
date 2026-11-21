"""Eval runner (ADR-0010): `uv run pytest -m evals`; paste the Markdown table into the PR.

EVAL_PREDICTED_DIR and EVAL_GOLDEN_DIR hold JSON files paired by file name.
"""

import copy
import os
from pathlib import Path

import pytest

from forms2json.domain.form_definition import FormDefinition
from tests.evals.metrics import Scores, score, to_markdown

pytestmark = pytest.mark.evals

DATA = Path(__file__).parents[3] / "data"
REFERENCES = [
    *DATA.glob("1. */konfiguracja_form_*.json"),
    *DATA.glob("5. */konfiguracja_form_*.json"),
]


def _load(path: Path) -> FormDefinition:
    return FormDefinition.from_json(path.read_text(encoding="utf-8"))


def _report(rows: dict[str, Scores], capsys: pytest.CaptureFixture[str]) -> None:
    with capsys.disabled():
        print("\n" + to_markdown(rows))


def test_dataset(capsys: pytest.CaptureFixture[str]) -> None:
    predicted_dir, golden_dir = (
        os.environ.get("EVAL_PREDICTED_DIR"),
        os.environ.get("EVAL_GOLDEN_DIR"),
    )
    if not predicted_dir or not golden_dir:
        pytest.skip("set EVAL_PREDICTED_DIR and EVAL_GOLDEN_DIR")
    rows = {}
    for golden in sorted(Path(golden_dir).glob("*.json")):
        predicted = Path(predicted_dir) / golden.name
        # A missing prediction scores as an empty form: zero recall, visible in the table.
        form = _load(predicted) if predicted.exists() else FormDefinition(title="")
        rows[golden.stem] = score(form, _load(golden))
    assert rows, f"no golden JSON in {golden_dir}"
    _report(rows, capsys)


def _broken(form: FormDefinition) -> FormDefinition:
    """A copy with one section dropped, one field type changed and one field's states cleared."""
    broken = copy.deepcopy(form)
    questions = broken.tabs[0].questions
    del questions[-1]
    fields = [q.field for q in questions[0].field.repeating_section_grid]
    fields[0].type = "TEXTAREA" if fields[0].type != "TEXTAREA" else "TEXT_FIELD"
    stated = next(q.field for tab in broken.tabs for q in tab.questions if q.field.states)
    stated.states = []
    return broken


def test_references_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    rows = {}
    for path in REFERENCES:
        golden = _load(path)
        name = path.parent.name.split(".")[0]
        rows[f"wzorzec {name}"] = same = score(golden, golden)
        rows[f"wzorzec {name} zepsuty"] = broken = score(_broken(golden), golden)
        assert same == Scores(0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        assert broken.section_recall < 1.0
        assert broken.type_accuracy < 1.0
        assert broken.condition_accuracy < 1.0
    _report(rows, capsys)
