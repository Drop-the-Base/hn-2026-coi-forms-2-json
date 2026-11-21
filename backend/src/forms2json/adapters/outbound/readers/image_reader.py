from forms2json.application.ports.document_reader import DocumentReader
from forms2json.application.ports.ocr_engine import OcrEngine
from forms2json.domain.document import NormalizedDocument, Page
from forms2json.domain.upload import JPEG, PNG


class ImageReader(DocumentReader):
    """A JPEG or PNG is one page read by OCR (FR-02).

    shortcut: no cutting of tall images into A4 pages, all scans in data/ are single A4 pages.
    """

    def __init__(self, ocr: OcrEngine) -> None:
        self._ocr = ocr

    def supports(self, mime_type: str) -> bool:
        return mime_type in (JPEG, PNG)

    def read(self, content: bytes) -> NormalizedDocument:
        return NormalizedDocument(pages=(Page(number=1, blocks=self._ocr.recognize(content)),))
