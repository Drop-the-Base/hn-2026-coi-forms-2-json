"""PDF reader on pdfplumber (ADR-0023): text lines and ruled tables in reading order per page.

Pages without a text layer (scans) go to OCR (ADR-0029).
"""

import io
from collections.abc import Iterator
from itertools import batched
from typing import Any

import pdfplumber
from pdfplumber.page import Page as PdfPage

from forms2json.adapters.outbound.readers.docx_reader import BOX_SPLIT, BOX_STATES
from forms2json.application.ports.document_reader import DocumentReader, ExtractionFailed
from forms2json.application.ports.ocr_engine import MAX_PIXELS, OcrEngine
from forms2json.domain.document import Block, Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.upload import PDF

# Guards against page bombs; the longest PDF in data/ (the standards guide) has 29 pages.
MAX_PAGES = 100
# Scans are rendered for OCR at the usual scanner resolution.
SCAN_DPI = 300


class PdfReader(DocumentReader):
    def __init__(self, ocr: OcrEngine) -> None:
        self._ocr = ocr

    def supports(self, mime_type: str) -> bool:
        return mime_type == PDF

    def read(self, content: bytes) -> NormalizedDocument:
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                if len(pdf.pages) > MAX_PAGES:
                    raise ExtractionFailed(f"PDF ma za dużo stron (maks. {MAX_PAGES}).")
                return NormalizedDocument(pages=tuple(map(self._page, pdf.pages)))
        except ExtractionFailed:
            raise
        # pdfminer raises many unrelated types (its own, TypeError, KeyError...) on crafted files.
        except Exception as error:
            message = "Plik jest uszkodzony albo ma nieprawidłową strukturę."
            raise ExtractionFailed(message) from error

    def _page(self, page: PdfPage) -> Page:
        if page.images and not page.chars:
            return Page(number=page.page_number, blocks=self._ocr.recognize(_render(page)))
        return Page(number=page.page_number, blocks=tuple(_blocks(page)))


def _render(page: PdfPage) -> bytes:
    """A page without a text layer (a scan) as PNG for OCR."""
    # Checked before rendering: a crafted page size would allocate gigabytes.
    if page.width * page.height * (SCAN_DPI / 72) ** 2 > MAX_PIXELS:
        raise ExtractionFailed(f"Strona {page.page_number} jest za duża do OCR.")
    png = io.BytesIO()
    page.to_image(resolution=SCAN_DPI).original.save(png, format="PNG")
    return png.getvalue()


def _blocks(page: PdfPage) -> Iterator[Block]:
    tables = page.find_tables()
    # Text inside a table is read with the table, so it is dropped from the free-text lines.
    free_text = page.filter(
        lambda obj: (
            obj.get("object_type") != "char"
            or not any(_inside(obj, table.bbox) for table in tables)
        )
    )
    placed: list[tuple[float, list[Block]]] = [
        (line["top"], list(_line(line["text"]))) for line in free_text.extract_text_lines()
    ]
    placed += [(table.bbox[1], [_table(table.extract())]) for table in tables]
    for _, blocks in sorted(placed, key=lambda item: item[0]):
        yield from blocks


def _inside(char: dict[str, Any], bbox: tuple[float, float, float, float]) -> bool:
    x0, top, x1, bottom = bbox
    x, y = (char["x0"] + char["x1"]) / 2, (char["top"] + char["bottom"]) / 2
    return bool(x0 <= x <= x1 and top <= y <= bottom)


def _line(text: str) -> Iterator[Block]:
    head, *rest = BOX_SPLIT.split(text)
    if head.strip():
        yield TextBlock(head.strip())
    for box, label in batched(rest, 2, strict=True):
        yield Checkbox(label=label.strip(), checked=BOX_STATES[box])


def _table(rows: list[list[str | None]]) -> Table:
    # Ruled forms split rows into many thin grid cells (merged ones come back as None), so,
    # as in the sheet readers, each row keeps only its non-empty cells in column order.
    return Table(rows=tuple(tuple(cell for cell in row if cell) for row in rows if any(row)))
