from typing import Any

from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.pipeline.understand_step import UnderstandStep
from forms2json.application.pipeline.validate_step import ValidatedForm
from forms2json.application.ports.llm_client import LlmUsage
from forms2json.domain.confidence import score
from forms2json.domain.cost import CostRates


class ReportStep(PipelineStep[ValidatedForm, dict[str, Any]]):
    """Job result: form, confidence (FR-T1), issues, LLM usage (NFR-13) and source text, as JSON.

    Reads the last-run state of the Understand and Compose steps, so all of them must belong
    to one pipeline built for one job (bootstrap.new_pipeline).
    """

    name = "report"

    def __init__(
        self,
        understand: UnderstandStep,
        compose: ComposeStep,
        review_threshold: float,
        cost_rates: CostRates,
    ) -> None:
        self._understand = understand
        self._compose = compose
        self._review_threshold = review_threshold
        self._cost_rates = cost_rates

    def run(self, data: ValidatedForm) -> dict[str, Any]:
        report = score(
            self._compose.confidence,
            data.issues,
            self._review_threshold,
            self._understand.ocr_confidence,
        )
        usage = self._understand.usage or LlmUsage(0, 0, 0.0)
        return {
            "form": data.form.to_dict(),
            "confidence": {
                "overall": report.overall,
                "elements": report.elements,
                "to_review": report.to_review,
            },
            "issues": [
                {"code": i.code, "message": i.message, "path": i.path, "severity": i.severity}
                for i in report.issues
            ],
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "seconds": usage.duration_seconds,
                "cost": self._cost_rates.total(
                    usage.prompt_tokens, usage.completion_tokens, usage.duration_seconds
                ),
                "currency": self._cost_rates.currency,
            },
            # the server drops the file (NFR-06), so the review screen shows this text instead
            "source_text": self._understand.source_text,
        }
