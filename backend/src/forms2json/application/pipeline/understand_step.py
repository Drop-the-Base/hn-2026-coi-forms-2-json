from pathlib import Path
from typing import Any

from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.llm_client import LlmCallFailed, LlmClient, LlmResult, LlmUsage
from forms2json.domain.document import Checkbox, NormalizedDocument, Table, TextBlock
from forms2json.domain.form_draft import (
    DRAFT_ADDITION_SCHEMA,
    FORM_DRAFT_SCHEMA,
    DraftAddition,
    FormDraft,
    InvalidFormDraft,
)

PROMPTS = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (PROMPTS / "understand_v3.md").read_text(encoding="utf-8")
FILL_PROMPT = f"{SYSTEM_PROMPT}\n\n{(PROMPTS / 'understand_fill.md').read_text(encoding='utf-8')}"


class DocumentTooLong(ValueError):
    """The document text exceeds the LLM input limit (guardrail, coding-rules §2.4)."""


def serialize(document: NormalizedDocument) -> str:
    lines: list[str] = []
    for page in document.pages:
        lines.append(f"## Strona {page.number}")
        for block in page.blocks:
            match block:
                case TextBlock(text):
                    lines.append(text)
                case Table(rows):
                    lines.extend("| " + " | ".join(row) + " |" for row in rows)
                case Checkbox(label, checked):
                    lines.append(f"{'☒' if checked else '☐'} {label}")
    return "\n".join(lines)


class UnderstandStep(PipelineStep[NormalizedDocument, FormDraft]):
    """NormalizedDocument → FormDraft via the LLM (FR-07, FR-T1).

    Invalid output gets one retry with the validation error in the prompt, then
    InvalidFormDraft propagates. A second, fill-in call then adds the fields the answer missed
    (the model skips different ones each run); if it fails, the first answer stands.
    `usage` sums all calls of the last run, failed or not (NFR-13).
    `source_text` keeps the last serialized document for the review screen (FR-E4).
    `ocr_confidence` is the last document's, for the confidence report (FR-T1).
    """

    name = "understand"

    def __init__(self, llm: LlmClient, max_input_chars: int) -> None:
        self._llm = llm
        self._max_input_chars = max_input_chars
        self.usage: LlmUsage | None = None
        self.source_text = ""
        self.ocr_confidence: float | None = None

    def run(self, data: NormalizedDocument) -> FormDraft:
        text = self.source_text = serialize(data)
        # shortcut: no chunking, a longer document fails; split by pages when real files hit it.
        if len(text) > self._max_input_chars:
            raise DocumentTooLong(f"{len(text)} chars > limit {self._max_input_chars}")
        self.usage = None
        self.ocr_confidence = data.ocr_confidence
        try:
            draft = self._ask(text)
        except InvalidFormDraft as error:
            retry = f"{text}\n\nPoprzednia odpowiedź była niepoprawna, popraw ją:\n{error}"
            draft = self._ask(retry)
        return self._fill(text, draft)

    def _ask(self, user: str) -> FormDraft:
        result = self._call(SYSTEM_PROMPT, user, FORM_DRAFT_SCHEMA)
        return FormDraft.from_dict(result.data)

    def _fill(self, text: str, draft: FormDraft) -> FormDraft:
        # options too: without them a choice field looks empty and its options come back as fields
        listing = "\n".join(
            f"- [{f.section}] {f.type}: {f.label} ({f.key})"
            + (f", opcje: {'; '.join(f.options)}" if f.options else "")
            for f in draft.fields
        )
        try:
            result = self._call(
                FILL_PROMPT,
                f"{text}\n\n## Pola z pierwszej rundy\n{listing}",
                DRAFT_ADDITION_SCHEMA,
            )
            return DraftAddition.from_dict(result.data).added_to(draft)
        except LlmCallFailed, InvalidFormDraft:
            return draft  # the fill-in only completes, the first answer is a whole form already

    def _call(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        result = self._llm.generate_json(system, user, schema)
        self.usage = result.usage if self.usage is None else _add(self.usage, result.usage)
        return result


def _add(a: LlmUsage, b: LlmUsage) -> LlmUsage:
    return LlmUsage(
        a.prompt_tokens + b.prompt_tokens,
        a.completion_tokens + b.completion_tokens,
        a.duration_seconds + b.duration_seconds,
    )
