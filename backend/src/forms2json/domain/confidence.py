"""Confidence score (FR-T1): per element, overall, elements to review and the issues behind them.

Elements are keyed by their JSON path in the FormDefinition
(e.g. ``tabs[0].questionGrid[1].field``), the same paths the rules put in ``Issue.path``.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from forms2json.domain.rules import Issue, Severity

# Penalty per issue, subtracted from the source confidence and floored at 0.
# An ERROR breaks the output, a WARNING is a Standards deviation the official forms also make.
PENALTIES = {Severity.ERROR: 0.3, Severity.WARNING: 0.1}


@dataclass(frozen=True)
class ConfidenceReport:
    elements: dict[str, float]
    overall: float
    to_review: list[str]
    issues: list[Issue]


def score(
    sources: Mapping[str, float], issues: list[Issue], review_threshold: float
) -> ConfidenceReport:
    """Combine source confidences (OCR/LLM, 1.0 for predefined blocks) with rule penalties.

    An issue penalises every element whose path is a prefix of the issue path: the element itself
    and the elements that contain it (a field error also lowers its section and tab).
    """
    elements = {
        path: max(0.0, conf - sum(PENALTIES[i.severity] for i in issues if _within(i.path, path)))
        for path, conf in sources.items()
    }
    # shortcut: equal weights per element, upgrade when the evals show which elements matter more.
    # Nothing extracted is not a confident result, so an empty form scores 0.
    overall = sum(elements.values()) / len(elements) if elements else 0.0
    to_review = [path for path, conf in elements.items() if conf < review_threshold]
    return ConfidenceReport(elements, overall, to_review, issues)


def _within(issue_path: str, element_path: str) -> bool:
    rest = issue_path.removeprefix(element_path)
    return issue_path.startswith(element_path) and rest[:1] in ("", ".", "[")
