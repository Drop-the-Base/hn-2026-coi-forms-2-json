from dataclasses import dataclass

from forms2json.application.pipeline.step import PipelineStep
from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.rules import Issue, check_rules
from forms2json.domain.standards import check_schema, check_standards


@dataclass(frozen=True)
class ValidatedForm:
    form: FormDefinition
    issues: list[Issue]


class ValidateStep(PipelineStep[FormDefinition, ValidatedForm]):
    """Last pipeline step: rules R, Standards S and the official schema (FR-08, FR-09)."""

    name = "validate"

    def run(self, data: FormDefinition) -> ValidatedForm:
        issues = check_rules(data) + check_standards(data) + check_schema(data.to_dict())
        return ValidatedForm(data, issues)
