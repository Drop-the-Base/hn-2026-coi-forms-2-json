from collections import Counter
from pathlib import Path

import pytest

from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.domain.form_definition import Field, FormDefinition, JsonObject, JsonValue, Question
from forms2json.domain.form_draft import FormDraft
from forms2json.domain.rules import Severity, check_rules
from forms2json.domain.standards import check_standards
from tests.evals.metrics import score

DATA = Path(__file__).parents[3] / "data"
KINDS = [{"kind": k, "confidence": 1.0} for k in ("SELF", "OTHER_PERSON", "LEGAL_ENTITY")]


def _field(
    key: str, label: str, section: str, type_: str = "TEXT_FIELD", **extra: JsonValue
) -> JsonValue:
    field: JsonObject = {
        "key": key,
        "label": label,
        "section": section,
        "type": type_,
        "required": True,
        "options": [],
        "confidence": 0.9,
    }
    return field | extra


def _draft(title: str, addressee: str, fields: list[JsonValue], **extra: JsonValue) -> FormDraft:
    base = {
        "title": {"value": title, "confidence": 1.0},
        "addressee": {"value": addressee, "confidence": 1.0},
        "applicants": KINDS,
        "fields": fields,
        "conditions": [],
        "attachments": [],
        "fees": [],
        "consents": [],
    }
    return FormDraft.model_validate(base | extra)


ZWROT = "Zwrócić przelewem na rachunek bankowy"
ZALICZ = "Zaliczyć na poczet przyszłego zobowiązania podatkowego"
OVERPAYMENT = "Informacje o nadpłacie"
SETTLEMENT = "Rozliczenie nadpłaty"
# Hand-made draft of reference 5, as the Understand step should read the source document.
DRAFT_5 = _draft(
    "Wniosek o stwierdzenie nadpłaty podatku",
    "Urząd Miasta",
    [
        _field("podatek", "Podatek, którego dotyczy nadpłata", OVERPAYMENT),
        _field("kwota", "Kwota", OVERPAYMENT, "NUMBER"),
        _field("uzasadnienie", "Uzasadnienie", OVERPAYMENT, "TEXTAREA"),
        _field(
            "co", "Wybierz, co mamy zrobić z nadpłatą", SETTLEMENT, "RADIO", options=[ZALICZ, ZWROT]
        ),
        _field("nazwa", "Nazwa podatku", SETTLEMENT),
        _field("rachunek", "Numer rachunku", SETTLEMENT, confidence=0.8),
    ],
    conditions=[
        {"target": "nazwa", "source": "co", "value": ZALICZ, "confidence": 1.0},
        {"target": "rachunek", "source": "co", "value": ZWROT, "confidence": 0.6},
    ],
    attachments=[{"name": "Plik deklaracji podatkowej", "required": True, "confidence": 0.7}],
)
BUILDING = "Lokalizacja budynku"
DRAFT_1 = _draft(
    "Wniosek o ustalenie numeru porządkowego nieruchomości",
    "Do Wójta Gminy",
    [
        _field("miejscowosc", "Miejscowość", BUILDING),
        _field("obreb", "Obręb", BUILDING),
        _field("dzialka", "Numer ewidencyjny działki", BUILDING),
        _field("ulica", "Ulica", BUILDING),
    ],
)


def _fields(form: FormDefinition) -> list[Field]:
    def walk(questions: list[Question]) -> list[Field]:
        return [f for q in questions for f in (q.field, *walk(q.field.repeating_section_grid))]

    return [f for tab in form.tabs for f in walk(tab.questions)]


def _reference(number: int) -> FormDefinition:
    (path,) = DATA.glob(f"{number}. */konfiguracja_form_*.json")
    return FormDefinition.from_json(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("draft", "number"), [(DRAFT_1, 1), (DRAFT_5, 5)], ids=["1", "5"])
def test_draft_composes_close_to_reference(draft: FormDraft, number: int) -> None:
    form = ComposeStep().run(draft)

    issues = check_rules(form) + check_standards(form)
    assert [i for i in issues if i.severity is Severity.ERROR] == []
    scores = score(form, _reference(number))
    assert scores.rule_errors == 0
    assert scores.section_recall >= 0.8
    assert scores.field_recall >= 0.8
    assert scores.type_accuracy == 1.0


def test_pages_keep_standard_order_and_linear_flow() -> None:
    form = ComposeStep().run(DRAFT_5)

    assert [t.title for t in form.tabs] == [
        "Dane",
        OVERPAYMENT,
        "Kontakt i zgody",
        "Strona końcowa",
    ]
    assert [(link.source, link.target) for link in form.links] == [
        (a.id, b.id) for a, b in zip(form.tabs, form.tabs[1:], strict=False)
    ]


def test_subject_fields_keep_document_order_and_unique_tech_names() -> None:
    form = ComposeStep().run(DRAFT_5)

    subject = form.tabs[1]
    names = [
        [c.field.title for c in sorted(s.field.repeating_section_grid, key=lambda c: c.y)]
        for s in sorted(subject.questions, key=lambda q: q.y)
    ]
    assert names == [
        ["Podatek, którego dotyczy nadpłata", "Kwota", "Uzasadnienie"],
        ["Wybierz, co mamy zrobić z nadpłatą", "Nazwa podatku", "Numer rachunku"],
        ["Plik deklaracji podatkowej"],
    ]
    counts = Counter(f.tech_name for f in _fields(form))
    assert [name for name, n in counts.items() if n > 1] == []


def test_condition_gives_show_state_matching_reference() -> None:
    step = ComposeStep()
    form = step.run(DRAFT_5)

    golden = {f.tech_name: f.states for f in _fields(_reference(5))}
    for name in ("nazwa_podatku", "numer_rachunku"):
        states = next(f.states for f in _fields(form) if f.tech_name == name)
        assert states == golden[name]
        assert states is not None and [s.type for s in states] == ["SHOW"]
    assert step.confidence["numer_rachunku"] == 0.6  # min of field 0.8 and condition 0.6
    assert step.confidence["plik_deklaracji_podatkowej"] == 0.7


def test_fees_become_info_section_with_payment_proof() -> None:
    fee: JsonValue = {"description": "Opłata skarbowa", "amount": 17.0, "confidence": 0.5}
    form = ComposeStep().run(_draft("Wniosek", "Urząd", [], fees=[fee]))

    fees = form.tabs[1].questions[-1].field
    assert [c.field.type for c in fees.repeating_section_grid] == ["TEXT_BLOCK", "FILE_UPLOADER"]
    assert "Opłata skarbowa: 17,00 zł" in fees.repeating_section_grid[0].field.description
    assert [i for i in check_rules(form) if i.severity is Severity.ERROR] == []


def test_draft_without_subject_fields_skips_the_subject_page() -> None:
    form = ComposeStep().run(_draft("Wniosek", "Urząd", []))

    assert [t.title for t in form.tabs] == ["Dane", "Kontakt i zgody", "Strona końcowa"]
