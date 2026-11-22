from typing import Any

import pytest

from forms2json.application.pipeline.understand_step import (
    DocumentTooLong,
    UnderstandStep,
    serialize,
)
from forms2json.application.ports.llm_client import (
    LlmCallFailed,
    LlmClient,
    LlmResult,
    LlmUsage,
)
from forms2json.domain.document import Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.form_draft import (
    DRAFT_ADDITION_SCHEMA,
    FORM_DRAFT_SCHEMA,
    InvalidFormDraft,
)

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
NOTHING_MISSING: dict[str, Any] = {"fields": [], "conditions": []}


class FakeLlm(LlmClient):
    def __init__(self, *answers: dict[str, Any] | Exception) -> None:
        self._answers = list(answers)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        self.calls.append((system, user, schema))
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return LlmResult(answer, LlmUsage(10, 5, 1.0))


def test_serialize_writes_pages_tables_and_checkboxes() -> None:
    assert serialize(DOCUMENT) == (
        "## Strona 1\nWNIOSEK O COŚ\n| Data | Kwota |\n|  |  |\n## Strona 2\n☐ gotówka\n☒ przelew"
    )


def test_valid_answer_becomes_form_draft() -> None:
    llm = FakeLlm(VALID, NOTHING_MISSING)
    step = UnderstandStep(llm, max_input_chars=10_000)

    draft = step.run(DOCUMENT)

    assert draft.fields[0].key == "data"
    (_, user, schema), (_, fill_user, fill_schema) = llm.calls
    assert "## Strona 1" in user
    assert schema is FORM_DRAFT_SCHEMA
    assert "[A] DATEPICKER: Data (data)\n" in fill_user + "\n"
    assert fill_schema is DRAFT_ADDITION_SCHEMA
    assert step.usage == LlmUsage(20, 10, 2.0)


def test_invalid_answer_is_retried_with_the_error() -> None:
    llm = FakeLlm(INVALID, VALID, NOTHING_MISSING)
    step = UnderstandStep(llm, max_input_chars=10_000)

    draft = step.run(DOCUMENT)

    assert draft.title.value == "Wniosek o coś"
    assert "niepoprawna" in llm.calls[1][1]
    assert "title" in llm.calls[1][1]
    assert step.usage == LlmUsage(30, 15, 3.0)


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


def _field(key: str, section: str) -> dict[str, Any]:
    field: dict[str, Any] = VALID["fields"][0]
    return field | {"key": key, "label": key, "section": section}


def test_fill_in_adds_missing_fields_after_their_section() -> None:
    choice = _field("a1", "A") | {"type": "RADIO", "options": ["tak", "nie"]}
    first = VALID | {"fields": [choice, _field("b1", "B")]}
    missing = {
        "fields": [
            _field("a2", "A"),
            _field("b1", "B"),
            _field("c1", "C"),
            _field("c1_again", "C") | {"label": "C1"},  # same label, other key: a repeat
        ],
        "conditions": [
            {"target": "a2", "source": "a1", "value": "x", "confidence": 0.9},
            {"target": "a2", "source": "nie_ma", "value": "x", "confidence": 0.9},
        ],
    }

    llm = FakeLlm(first, missing)
    draft = UnderstandStep(llm, max_input_chars=10_000).run(DOCUMENT)

    assert "RADIO: a1 (a1), opcje: tak; nie" in llm.calls[1][1]
    assert [f.key for f in draft.fields] == ["a1", "a2", "b1", "c1"]
    assert [(c.target, c.source) for c in draft.conditions] == [("a2", "a1")]


@pytest.mark.parametrize("failure", [LlmCallFailed("timeout"), INVALID])
def test_failed_fill_in_keeps_the_first_answer(failure: dict[str, Any] | Exception) -> None:
    draft = UnderstandStep(FakeLlm(VALID, failure), max_input_chars=10_000).run(DOCUMENT)

    assert [f.key for f in draft.fields] == ["data"]
