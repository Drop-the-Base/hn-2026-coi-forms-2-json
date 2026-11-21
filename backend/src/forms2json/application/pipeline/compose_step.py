from forms2json.application.pipeline.step import PipelineStep
from forms2json.domain.compose import Confidence, compose
from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.form_draft import FormDraft


class ComposeStep(PipelineStep[FormDraft, FormDefinition]):
    """FormDraft → FormDefinition without AI (FR-07, FR-09, K-14).

    `confidence` holds the last run's per-element confidence, keyed by techName (FR-T1).
    """

    name = "compose"

    def __init__(self) -> None:
        self.confidence: Confidence = {}

    def run(self, data: FormDraft) -> FormDefinition:
        form, self.confidence = compose(data)
        return form
