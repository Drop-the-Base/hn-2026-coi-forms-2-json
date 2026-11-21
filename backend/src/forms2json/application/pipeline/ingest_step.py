from collections.abc import Sequence

from forms2json.application.pipeline.step import PipelineStep
from forms2json.application.ports.document_reader import DocumentReader
from forms2json.domain.document import NormalizedDocument, SourceFile


class UnsupportedFormat(ValueError):
    """No reader for this MIME type."""


class IngestStep(PipelineStep[SourceFile, NormalizedDocument]):
    """SourceFile → NormalizedDocument with the first reader that supports its MIME type."""

    name = "ingest"

    def __init__(self, readers: Sequence[DocumentReader]) -> None:
        self._readers = readers

    def run(self, data: SourceFile) -> NormalizedDocument:
        for reader in self._readers:
            if reader.supports(data.mime_type):
                return reader.read(data.content)
        raise UnsupportedFormat(f"Format {data.mime_type} jeszcze nieobsługiwany")
