from pathlib import Path

from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.llm_client import LlmClient, LlmUsage
from forms2json.domain.document import Checkbox, NormalizedDocument, Table, TextBlock
from forms2json.domain.form_draft import FORM_DRAFT_SCHEMA, FormDraft, InvalidFormDraft

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "understand_v4.md").read_text(encoding="utf-8")


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
    InvalidFormDraft propagates. `usage` sums both attempts of the last run, failed or not (NFR-13).
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
            return self._ask(text)
        except InvalidFormDraft as error:
            retry = f"{text}\n\nPoprzednia odpowiedź była niepoprawna, popraw ją:\n{error}"
            return self._ask(retry)

    def _ask(self, user: str) -> FormDraft:
        result = self._llm.generate_json(SYSTEM_PROMPT, user, FORM_DRAFT_SCHEMA)
        self.usage = result.usage if self.usage is None else _add(self.usage, result.usage)
        return FormDraft.from_dict(result.data)


def _add(a: LlmUsage, b: LlmUsage) -> LlmUsage:
    return LlmUsage(
        a.prompt_tokens + b.prompt_tokens,
        a.completion_tokens + b.completion_tokens,
        a.duration_seconds + b.duration_seconds,
    )
