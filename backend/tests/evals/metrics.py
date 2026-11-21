"""Deterministic quality metrics of a predicted form JSON against a golden one (ADR-0010, FR-T4).

Elements are matched by techName: it is unique in a form, while labels repeat ("Ulica" sits
twice in one section) or are empty (TEXT_BLOCK).
"""

from collections.abc import Iterator
from dataclasses import dataclass

from forms2json.domain.form_definition import Field, FormDefinition, Question
from forms2json.domain.rules import SECTION_TYPES, Severity, check_rules

# shortcut: techName match punishes a right field under a different techName; switch to
# normalized labels with a tie-breaker when predictions name fields differently from the goldens.
# shortcut: no confidence-vs-errors calibration, the output JSON has no confidence yet; add it
# when the pipeline emits confidence.


@dataclass(frozen=True)
class Scores:
    rule_errors: int
    section_precision: float
    section_recall: float
    field_precision: float
    field_recall: float
    type_accuracy: float
    condition_accuracy: float


def score(predicted: FormDefinition, golden: FormDefinition) -> Scores:
    pred, gold = _elements(predicted), _elements(golden)
    pred_sections = {k for k, f in pred.items() if f.type in SECTION_TYPES}
    gold_sections = {k for k, f in gold.items() if f.type in SECTION_TYPES}
    pred_fields, gold_fields = pred.keys() - pred_sections, gold.keys() - gold_sections
    matched_fields = pred_fields & gold_fields
    with_states = [k for k in pred.keys() & gold.keys() if pred[k].states or gold[k].states]
    return Scores(
        rule_errors=sum(i.severity is Severity.ERROR for i in check_rules(predicted)),
        section_precision=_ratio(len(pred_sections & gold_sections), len(pred_sections)),
        section_recall=_ratio(len(pred_sections & gold_sections), len(gold_sections)),
        field_precision=_ratio(len(matched_fields), len(pred_fields)),
        field_recall=_ratio(len(matched_fields), len(gold_fields)),
        type_accuracy=_ratio(
            sum(pred[k].type == gold[k].type for k in matched_fields), len(matched_fields)
        ),
        condition_accuracy=_ratio(
            sum(_states(pred[k]) == _states(gold[k]) for k in with_states), len(with_states)
        ),
    )


def to_markdown(rows: dict[str, Scores]) -> str:
    lines = [
        "| przypadek | błędy reguł | sekcje P | sekcje R | pola P | pola R | typy | warunki |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, s in rows.items():
        ratios = (
            s.section_precision,
            s.section_recall,
            s.field_precision,
            s.field_recall,
            s.type_accuracy,
            s.condition_accuracy,
        )
        lines.append(
            f"| {name} | {s.rule_errors} | " + " | ".join(f"{r:.2f}" for r in ratios) + " |"
        )
    return "\n".join(lines)


def _elements(form: FormDefinition) -> dict[str, Field]:
    def walk(questions: list[Question]) -> Iterator[Field]:
        for q in questions:
            yield q.field
            yield from walk(q.field.repeating_section_grid)

    return {f.tech_name: f for tab in form.tabs for f in walk(tab.questions)}


def _states(field: Field) -> set[tuple[str, str]]:
    # Whitespace in JSONata carries no meaning; the references mix \r\n and spaces.
    return {(s.type, " ".join(s.query.split())) for s in field.states or []}


def _ratio(hits: int, total: int) -> float:
    # Nothing to find or nothing predicted counts as perfect, so the score does not divide by zero.
    return hits / total if total else 1.0
