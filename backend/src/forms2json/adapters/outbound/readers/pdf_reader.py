"""PDF reader on pdfplumber (ADR-0023): text lines and ruled tables in reading order per page."""

import io
from collections.abc import Iterator
from itertools import batched
from typing import Any

import pdfplumber
from pdfplumber.page import Page as PdfPage

from forms2json.adapters.outbound.readers.docx_reader import BOX_SPLIT, BOX_STATES
from forms2json.application.ports.document_reader import DocumentReader
from forms2json.domain.document import Block, Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.upload import PDF

# Guards against page bombs; the longest PDF in data/ (the standards guide) has 29 pages.
MAX_PAGES = 100


class ScannedPdf(ValueError):
    """A page has images but no text layer, so the PDF needs OCR (#25)."""


class PdfReader(DocumentReader):
    def supports(self, mime_type: str) -> bool:
        return mime_type == PDF

    def read(self, content: bytes) -> NormalizedDocument:
        # shortcut: a ValueError subclass until ExtractionFailed (#77) lands, then derive from it.
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise ValueError(f"PDF ma za dużo stron (maks. {MAX_PAGES})")
            return NormalizedDocument(pages=tuple(map(_page, pdf.pages)))


def _page(page: PdfPage) -> Page:
    if page.images and not page.chars:
        raise ScannedPdf(f"Strona {page.page_number} nie ma warstwy tekstowej (skan), wymaga OCR")
    return Page(number=page.page_number, blocks=tuple(_blocks(page)))


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
