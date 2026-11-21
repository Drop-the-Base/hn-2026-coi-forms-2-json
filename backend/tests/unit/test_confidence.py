import pytest

from forms2json.domain.confidence import score
from forms2json.domain.rules import Issue, Severity

TAB = "tabs[0]"
FIELD = "tabs[0].questionGrid[0].field"
OTHER = "tabs[0].questionGrid[1].field"


def test_without_issues_overall_is_mean_of_sources() -> None:
    report = score({TAB: 1.0, FIELD: 0.8, OTHER: 0.6}, [], review_threshold=0.85)

    assert report.elements == {TAB: 1.0, FIELD: 0.8, OTHER: 0.6}
    assert report.overall == pytest.approx(0.8)


def test_error_lowers_element_its_parents_and_overall() -> None:
    issue = Issue("R-X", "błąd", f"{FIELD}.validation")

    report = score({TAB: 1.0, FIELD: 0.9, OTHER: 0.9}, [issue], review_threshold=0.85)

    assert report.elements[FIELD] == pytest.approx(0.6)
    assert report.elements[TAB] == pytest.approx(0.7)
    assert report.elements[OTHER] == 0.9
    assert report.overall == pytest.approx((0.7 + 0.6 + 0.9) / 3)
    assert report.issues == [issue]


def test_warning_costs_less_than_error_and_floors_at_zero() -> None:
    warning = Issue("S-X", "uwaga", FIELD, Severity.WARNING)
    errors = [Issue("R-X", "błąd", OTHER)] * 4

    report = score({FIELD: 0.9, OTHER: 0.9}, [warning, *errors], review_threshold=0.85)

    assert report.elements[FIELD] == pytest.approx(0.8)
    assert report.elements[OTHER] == 0.0


def test_sibling_with_common_prefix_is_not_penalised() -> None:
    report = score({"tabs[1]": 1.0}, [Issue("R-X", "błąd", "tabs[10]")], review_threshold=0.85)

    assert report.elements["tabs[1]"] == 1.0


def test_threshold_selects_elements_to_review() -> None:
    report = score({TAB: 1.0, FIELD: 0.84, OTHER: 0.85}, [], review_threshold=0.85)

    assert report.to_review == [FIELD]


def test_empty_form_scores_zero() -> None:
    report = score({}, [], review_threshold=0.85)

    assert report.elements == {}
    assert report.overall == 0.0
    assert report.to_review == []


def test_ocr_confidence_caps_every_element() -> None:
    report = score({TAB: 1.0, FIELD: 0.6}, [], review_threshold=0.85, ocr_confidence=0.9)

    assert report.elements == {TAB: 0.9, FIELD: 0.6}
    assert report.issues == []


def test_low_ocr_confidence_is_a_warning_and_sends_all_to_review() -> None:
    report = score({TAB: 1.0, FIELD: 0.9}, [], review_threshold=0.85, ocr_confidence=0.7)

    assert report.to_review == [TAB, FIELD]
    assert [(i.code, i.severity) for i in report.issues] == [
        ("OCR-LOW-CONFIDENCE", Severity.WARNING)
    ]
