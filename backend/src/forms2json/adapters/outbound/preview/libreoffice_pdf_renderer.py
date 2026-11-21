from collections.abc import Callable

from forms2json.adapters.outbound.libreoffice import SofficeFailed, soffice_convert
from forms2json.application.ports.pdf_renderer import PdfRenderer, PreviewFailed
from forms2json.domain.upload import DOC, DOCX, ODS, XLSX

# soffice picks the import filter by content, the suffix only helps (a .doc may be DOCX inside).
SUFFIXES = {DOC: ".doc", DOCX: ".docx", XLSX: ".xlsx", ODS: ".ods"}

FAILED = "Nie udało się przygotować podglądu (plik uszkodzony albo konwersja trwała za długo)."


class LibreOfficePdfRenderer(PdfRenderer):
    def __init__(
        self,
        timeout_seconds: float,
        convert: Callable[[bytes, str, str, float], bytes] = soffice_convert,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._convert = convert

    def render(self, content: bytes, mime_type: str) -> bytes:
        try:
            return self._convert(content, SUFFIXES[mime_type], "pdf", self._timeout_seconds)
        except SofficeFailed as error:
            raise PreviewFailed(FAILED) from error
