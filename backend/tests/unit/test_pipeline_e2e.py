import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from forms2json.adapters.outbound.observability.log_observer import LogObserver
from forms2json.application.pipeline.ingest_step import UnsupportedFormat
from forms2json.application.ports.job_queue import Job
from forms2json.application.ports.llm_client import LlmClient, LlmResult, LlmUsage
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.bootstrap import pipeline_factory
from forms2json.config import Settings
from forms2json.domain.document import SourceFile
from forms2json.domain.form_draft import DRAFT_ADDITION_SCHEMA
from forms2json.domain.upload import DOCX
from tests.unit.test_compose_step import DRAFT_5
from tests.unit.test_process_job import FakeFileStore, FakeJobQueue

DATA = Path(__file__).parents[3] / "data"
(DOCX_5,) = DATA.glob("5. */Wniosek o stwierdzenie nadpłaty podatku.docx")
VALID = DRAFT_5.model_dump(mode="json")
NOTHING_MISSING: dict[str, Any] = {"fields": [], "conditions": []}


class FakeLlm(LlmClient):
    """Answers in order, the fill-in finds nothing missing; each call costs 10 + 5 tokens, 1 s."""

    def __init__(self, *answers: dict[str, Any]) -> None:
        self._answers = list(answers)

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        answer = NOTHING_MISSING if schema is DRAFT_ADDITION_SCHEMA else self._answers.pop(0)
        return LlmResult(answer, LlmUsage(10, 5, 1.0))


def _run(llm: LlmClient, mime_type: str = DOCX) -> object:
    return pipeline_factory(Settings(), llm)(LogObserver()).run(
        SourceFile(DOCX_5.read_bytes(), mime_type)
    )


def test_docx_becomes_form_with_confidence_issues_usage_and_source_text() -> None:
    result = _run(FakeLlm(VALID))

    assert isinstance(result, dict)
    json.dumps(result)  # the queue adapter serializes it
    assert set(result) == {"form", "confidence", "issues", "usage", "source_text"}
    assert result["form"]["title"] == DRAFT_5.title.value
    assert [i for i in result["issues"] if i["severity"] == "ERROR"] == []
    confidence = result["confidence"]
    assert 0 < confidence["overall"] <= 1
    assert confidence["elements"]["tabs[0]"] == 1.0
    # numer_rachunku: field 0.8, condition 0.6 -> below the 0.85 review threshold
    assert any(confidence["elements"][p] == 0.6 for p in confidence["to_review"])
    assert result["usage"] == {
        "prompt_tokens": 20,  # the answer and the fill-in call
        "completion_tokens": 10,
        "seconds": 2.0,
        "cost": 0.0,  # rates default to 0
        "currency": "USD",
    }
    assert result["source_text"].startswith("## Strona 1\n")
    assert "nadpłat" in result["source_text"]


def test_usage_cost_comes_from_configured_rates() -> None:
    settings = Settings(
        cost_per_1m_input_tokens=1_000_000, cost_per_1m_output_tokens=2_000_000, cost_currency="PLN"
    )
    pipeline = pipeline_factory(settings, FakeLlm(VALID))(LogObserver())

    result = pipeline.run(SourceFile(DOCX_5.read_bytes(), DOCX))

    # 20 input tokens at 1 per token + 10 output tokens at 2 per token (answer + fill-in)
    assert isinstance(result, dict)
    assert (result["usage"]["cost"], result["usage"]["currency"]) == (40.0, "PLN")


def test_unsupported_format_fails_with_readable_error() -> None:
    with pytest.raises(UnsupportedFormat, match="text/plain jeszcze nieobsługiwany"):
        _run(FakeLlm(), "text/plain")


def test_usage_does_not_leak_between_jobs() -> None:
    # Job 1 needs a retry (3 calls with the fill-in), job 2 two; one LLM client like in the worker.
    llm = FakeLlm({"title": "no"}, VALID, VALID)
    files, queue = FakeFileStore(), FakeJobQueue()
    use_case = ProcessJob(files, pipeline_factory(Settings(), llm), queue)
    for _ in range(2):
        job = Job(uuid.uuid4(), DOCX)
        files.save(str(job.job_id), DOCX_5.read_bytes())
        asyncio.run(use_case.execute(job))

    assert [r.result["usage"]["prompt_tokens"] for r in queue.results] == [30, 20]
