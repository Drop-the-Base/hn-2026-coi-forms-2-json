import io

from openpyxl import load_workbook

from forms2json.application.ports.document_reader import DocumentReader
from forms2json.domain.document import NormalizedDocument, Page, Table
from forms2json.domain.upload import XLSX


class XlsxReader(DocumentReader):
    """One page per sheet, holding one table of the sheet's non-empty rows.

    Forms are drawn on a fine grid (up to ~130 columns), so each row keeps only its
    non-empty cells in column order. A merged cell's value sits in its top-left cell,
    the rest read as empty, so it appears once.
    """

    def supports(self, mime_type: str) -> bool:
        return mime_type == XLSX

    def read(self, content: bytes) -> NormalizedDocument:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            pages = []
            for number, sheet in enumerate(workbook.worksheets, start=1):
                rows = tuple(row for row in map(_row, sheet.iter_rows(values_only=True)) if row)
                pages.append(Page(number=number, blocks=(Table(rows=rows),) if rows else ()))
            return NormalizedDocument(pages=tuple(pages))
        finally:
            workbook.close()


def _row(values: tuple[object, ...]) -> tuple[str, ...]:
    texts = (str(value).strip() for value in values if value is not None)
    return tuple(text for text in texts if text)
