"""Old binary DOC: LibreOffice headless converts it to DOCX, then the DOCX reader reads it.

LibreOffice runs as an unmodified program, never linked (ADR-0013). A .doc that is DOCX inside
is detected as DOCX on upload, so it goes straight to DocxReader (FR-03).
"""

from collections.abc import Callable

from forms2json.adapters.outbound.libreoffice import SofficeFailed, soffice_convert
from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.application.ports.document_reader import DocumentReader, ExtractionFailed
from forms2json.domain.document import NormalizedDocument
from forms2json.domain.upload import DOC

FAILED = "Nie udało się przekonwertować pliku DOC (plik uszkodzony albo konwersja trwała za długo)."


def soffice_to_docx(content: bytes, timeout_seconds: float) -> bytes:
    try:
        return soffice_convert(content, ".doc", "docx", timeout_seconds)
    except SofficeFailed as error:
        raise ExtractionFailed(FAILED) from error


class DocReader(DocumentReader):
    def __init__(
        self,
        timeout_seconds: float,
        convert: Callable[[bytes, float], bytes] = soffice_to_docx,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._convert = convert
        self._docx = DocxReader()

    def supports(self, mime_type: str) -> bool:
        return mime_type == DOC

    def read(self, content: bytes) -> NormalizedDocument:
        return self._docx.read(self._convert(content, self._timeout_seconds))
