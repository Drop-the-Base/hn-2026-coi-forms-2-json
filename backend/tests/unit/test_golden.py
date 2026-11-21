"""Golden JSONs (FR-T4, ADR-0010) pass the technical rules, the Standards and the schema."""

import json
from pathlib import Path

import pytest

from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.rules import Severity, check_rules
from forms2json.domain.standards import check_schema, check_standards

DATASET = Path(__file__).parents[1] / "evals" / "dataset"
GOLDEN = sorted([*(DATASET / "golden").glob("*.json"), *(DATASET / "walidacja").glob("*.json")])
# Registry data (FR-E1) describe the applicant, so only the applicant's own blocks use them.
APPLICANT_SECTIONS = {"twoje_dane", "adres_zamieszkania", "dane_do_kontaktu"}


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.name)
def test_golden_passes_rules_and_schema(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    issues = check_rules(FormDefinition.from_json(text)) + check_schema(json.loads(text))
    # R-STATES references are WARNINGs in the rules, but a golden form must have none.
    bad = [i for i in issues if i.severity == Severity.ERROR or i.code == "R-STATES"]
    assert bad == []


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.name)
def test_golden_passes_standards(path: Path) -> None:
    assert check_standards(FormDefinition.from_json(path.read_text(encoding="utf-8"))) == []


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.name)
def test_golden_registry_data_only_in_applicant_sections(path: Path) -> None:
    form = FormDefinition.from_json(path.read_text(encoding="utf-8"))
    misplaced = [
        child.field.tech_name
        for tab in form.tabs
        for section in tab.questions
        for child in section.field.repeating_section_grid
        if child.field.default_value_type == "EXTERNAL_SYSTEM"
        and section.field.tech_name not in APPLICANT_SECTIONS
    ]
    assert misplaced == []
