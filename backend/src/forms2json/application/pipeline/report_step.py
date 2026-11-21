from typing import Any

from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.pipeline.understand_step import UnderstandStep
from forms2json.application.pipeline.validate_step import ValidatedForm
from forms2json.domain.confidence import score


class ReportStep(PipelineStep[ValidatedForm, dict[str, Any]]):
    """Job result: form, confidence (FR-T1), issues and LLM usage (NFR-13), ready for JSON.

    Reads the last-run state of the Understand and Compose steps, so all of them must belong
    to one pipeline built for one job (bootstrap.new_pipeline).
    """

    name = "report"

    def __init__(
        self, understand: UnderstandStep, compose: ComposeStep, review_threshold: float
    ) -> None:
        self._understand = understand
        self._compose = compose
        self._review_threshold = review_threshold

    def run(self, data: ValidatedForm) -> dict[str, Any]:
        report = score(self._compose.confidence, data.issues, self._review_threshold)
        usage = self._understand.usage
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
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "seconds": usage.duration_seconds if usage else 0.0,
            },
        }
