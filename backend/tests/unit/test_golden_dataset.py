"""Golden JSONs of the eval dataset (ADR-0010, FR-T4) stay valid under the rules and the schema."""

import json
from pathlib import Path

import pytest

from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.rules import Severity, check_rules
from forms2json.domain.standards import check_schema

GOLDEN = sorted((Path(__file__).parents[1] / "evals" / "dataset" / "golden").glob("*.json"))


def test_golden_dataset_is_not_empty() -> None:
    assert GOLDEN


@pytest.mark.parametrize("path", GOLDEN, ids=[p.stem for p in GOLDEN])
def test_golden_json_passes_rules_and_schema(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    issues = check_rules(FormDefinition.from_json(text))
    errors = [i for i in issues if i.severity is Severity.ERROR]
    assert errors + check_schema(json.loads(text)) == []
