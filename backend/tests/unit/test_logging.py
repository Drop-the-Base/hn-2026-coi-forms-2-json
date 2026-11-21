import asyncio
import json
import logging
import uuid

import httpx2
import pytest
from opentelemetry.sdk.trace import TracerProvider

from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.adapters.outbound.observability.log_observer import JobContextFilter, JobLog
from forms2json.application.ports.job_queue import Job
from forms2json.application.use_cases.process_job import ProcessJob
from forms2json.bootstrap import pipeline_factory
from forms2json.config import Settings
from forms2json.domain.upload import DOCX
from tests.unit.test_compose_step import DRAFT_5
from tests.unit.test_openai_compatible_client import completion
from tests.unit.test_pipeline_e2e import DOCX_5, VALID
from tests.unit.test_process_job import FakeFileStore, FakeJobQueue

API_KEY = "sk-test-secret-key"


def test_full_job_logs_job_and_trace_id_but_no_key_or_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    caplog.handler.addFilter(JobContextFilter())
    answer = json.dumps(VALID, ensure_ascii=False)
    http = httpx2.Client(transport=httpx2.MockTransport(lambda _: completion(answer)))
    llm = OpenAiCompatibleLlmClient("http://llm/v1", "m", 5.0, 100, http, api_key=API_KEY)
    files, queue = FakeFileStore(), FakeJobQueue()
    job = Job(uuid.uuid4(), DOCX)
    files.save(str(job.job_id), DOCX_5.read_bytes())
    use_case = ProcessJob(files, pipeline_factory(Settings(), llm), queue, [JobLog()])

    with TracerProvider().get_tracer(__name__).start_as_current_span("job") as span:
        asyncio.run(use_case.execute(job))
    trace_id = format(span.get_span_context().trace_id, "032x")

    assert queue.results[0].error is None
    messages = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("LLM m attempt 1/3: tokens in 10 out 5") for m in messages)
    assert any(m.startswith("Job done in") for m in messages)
    ours = [r for r in caplog.records if r.name.startswith("forms2json")]
    assert {(r.job_id, r.trace_id) for r in ours} == {(str(job.job_id), trace_id)}  # type: ignore[attr-defined]
    text = "\n".join(messages)
    assert API_KEY not in text
    assert DRAFT_5.title.value not in text  # from the document, also in the model's answer
