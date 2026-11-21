"""Golden JSONs (FR-T4, ADR-0010) pass the technical rules and the official schema."""

import json
from pathlib import Path

import pytest

from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.rules import Severity, check_rules
from forms2json.domain.standards import check_schema

GOLDEN = sorted((Path(__file__).parents[1] / "evals" / "dataset" / "golden").glob("*.json"))


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.name)
def test_golden_passes_rules_and_schema(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    issues = check_rules(FormDefinition.from_json(text)) + check_schema(json.loads(text))
    # R-STATES references are WARNINGs in the rules, but a golden form must have none.
    bad = [i for i in issues if i.severity == Severity.ERROR or i.code == "R-STATES"]
    assert bad == []
