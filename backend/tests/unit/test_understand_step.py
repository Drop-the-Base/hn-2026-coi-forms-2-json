from typing import Any

import pytest

from forms2json.application.pipeline.understand_step import (
    DocumentTooLong,
    UnderstandStep,
    serialize,
)
from forms2json.application.ports.llm_client import LlmClient, LlmResult, LlmUsage
from forms2json.domain.document import Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.form_draft import FORM_DRAFT_SCHEMA, InvalidFormDraft

DOCUMENT = NormalizedDocument(
    pages=(
        Page(1, (TextBlock("WNIOSEK O COŚ"), Table((("Data", "Kwota"), ("", ""))))),
        Page(2, (Checkbox("gotówka", checked=False), Checkbox("przelew", checked=True))),
    )
)

VALID: dict[str, Any] = {
    "title": {"value": "Wniosek o coś", "confidence": 0.9},
    "addressee": {"value": "Urząd", "confidence": 0.8},
    "applicants": [{"kind": "SELF", "confidence": 0.9}],
    "fields": [
        {
            "key": "data",
            "label": "Data",
            "section": "A",
            "type": "DATEPICKER",
            "required": True,
            "options": [],
            "confidence": 0.7,
        }
    ],
    "conditions": [],
    "attachments": [],
    "fees": [],
    "consents": [],
}
INVALID: dict[str, Any] = {"title": "no"}


class FakeLlm(LlmClient):
    def __init__(self, *answers: dict[str, Any]) -> None:
        self._answers = list(answers)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        self.calls.append((system, user, schema))
        return LlmResult(self._answers.pop(0), LlmUsage(10, 5, 1.0))


def test_serialize_writes_pages_tables_and_checkboxes() -> None:
    assert serialize(DOCUMENT) == (
        "## Strona 1\nWNIOSEK O COŚ\n| Data | Kwota |\n|  |  |\n## Strona 2\n☐ gotówka\n☒ przelew"
    )


def test_valid_answer_becomes_form_draft() -> None:
    llm = FakeLlm(VALID)
    step = UnderstandStep(llm, max_input_chars=10_000)

    draft = step.run(DOCUMENT)

    assert draft.fields[0].key == "data"
    ((_, user, schema),) = llm.calls
    assert "## Strona 1" in user
    assert schema is FORM_DRAFT_SCHEMA
    assert step.usage == LlmUsage(10, 5, 1.0)


def test_invalid_answer_is_retried_with_the_error() -> None:
    llm = FakeLlm(INVALID, VALID)
    step = UnderstandStep(llm, max_input_chars=10_000)

    draft = step.run(DOCUMENT)

    assert draft.title.value == "Wniosek o coś"
    assert "niepoprawna" in llm.calls[1][1]
    assert "title" in llm.calls[1][1]
    assert step.usage == LlmUsage(20, 10, 2.0)


def test_two_invalid_answers_raise() -> None:
    step = UnderstandStep(FakeLlm(INVALID, INVALID), max_input_chars=10_000)

    with pytest.raises(InvalidFormDraft):
        step.run(DOCUMENT)
    assert step.usage == LlmUsage(20, 10, 2.0)


def test_too_long_document_is_rejected_before_calling_the_llm() -> None:
    llm = FakeLlm()

    with pytest.raises(DocumentTooLong):
        UnderstandStep(llm, max_input_chars=10).run(DOCUMENT)
    assert llm.calls == []
