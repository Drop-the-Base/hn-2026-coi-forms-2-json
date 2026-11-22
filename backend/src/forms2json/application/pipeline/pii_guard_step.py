from collections import Counter
from dataclasses import replace

from forms2json.application.pipeline.step import PipelineStep
from forms2json.domain.document import Block, Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.pii import PERSONAL_IDS, mask_pii


class PiiGuardStep(PipelineStep[NormalizedDocument, NormalizedDocument]):
    """NormalizedDocument → the same document with personal data masked, before any LLM call.

    A file without a personal ID is a blank form and passes unchanged. `found` counts the masked
    data of the last run by kind (NFR-06), for the report and its metric.
    """

    name = "pii"

    def __init__(self) -> None:
        self.found: Counter[str] = Counter()

    def run(self, data: NormalizedDocument) -> NormalizedDocument:
        found: Counter[str] = Counter()
        masked = NormalizedDocument(
            tuple(
                Page(page.number, tuple(_mask(block, found) for block in page.blocks))
                for page in data.pages
            )
        )
        filled = not PERSONAL_IDS.isdisjoint(found)
        self.found = found if filled else Counter()
        return masked if filled else data


def _mask(block: Block, found: Counter[str]) -> Block:
    match block:
        case TextBlock(text):
            return replace(block, text=mask_pii(text, found))
        case Table(rows):
            return Table(tuple(tuple(mask_pii(cell, found) for cell in row) for row in rows))
        case Checkbox(label):
            return replace(block, label=mask_pii(label, found))
