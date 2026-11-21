import xml.etree.ElementTree as ET

from forms2json.adapters.outbound.readers.zip_archive import open_archive
from forms2json.application.ports.document_reader import DocumentReader
from forms2json.domain.document import NormalizedDocument, Page, Table
from forms2json.domain.upload import ODS

_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
# Repeated non-empty rows or cells add nothing for a form, and a tiny file can declare
# a million repeats, so expansion is capped.
_MAX_REPEAT = 100


class OdsReader(DocumentReader):
    """One page per sheet, holding one table of the sheet's non-empty rows.

    Same shape as XlsxReader: each row keeps only its non-empty cells in column order,
    and covered (merged) cells are skipped, so a merged value appears once.
    """

    def supports(self, mime_type: str) -> bool:
        return mime_type == ODS

    def read(self, content: bytes) -> NormalizedDocument:
        with open_archive(content) as archive:
            root = ET.fromstring(archive.read("content.xml"))
            pages = []
            # Inside the guard: a crafted repeat attribute fails in int() with ValueError.
            for number, sheet in enumerate(root.iter(f"{_TABLE}table"), start=1):
                rows = tuple(_rows(sheet))
                pages.append(Page(number=number, blocks=(Table(rows=rows),) if rows else ()))
        return NormalizedDocument(pages=tuple(pages))


def _rows(sheet: ET.Element) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    # iter() also reaches rows inside table:table-header-rows and table:table-row-group.
    for row in sheet.iter(f"{_TABLE}table-row"):
        cells: list[str] = []
        for cell in row.findall(f"{_TABLE}table-cell"):
            text = "\n".join(_paragraph(p) for p in cell.findall(f"{_TEXT}p")).strip()
            if text:
                cells.extend([text] * _repeat(cell, "number-columns-repeated"))
        if cells:
            rows.extend([tuple(cells)] * _repeat(row, "number-rows-repeated"))
    return rows


def _repeat(element: ET.Element, attribute: str) -> int:
    return min(int(element.get(f"{_TABLE}{attribute}", "1")), _MAX_REPEAT)


def _paragraph(element: ET.Element) -> str:
    parts = [element.text or ""]
    for child in element:
        if child.tag == f"{_TEXT}s":
            parts.append(" " * min(int(child.get(f"{_TEXT}c", "1")), _MAX_REPEAT))
        elif child.tag == f"{_TEXT}tab":
            parts.append("\t")
        elif child.tag == f"{_TEXT}line-break":
            parts.append("\n")
        else:
            parts.append(_paragraph(child))
        parts.append(child.tail or "")
    return "".join(parts)
