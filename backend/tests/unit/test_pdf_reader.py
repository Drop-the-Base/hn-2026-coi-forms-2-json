from pathlib import Path

import pytest

from forms2json.adapters.outbound.readers import pdf_reader
from forms2json.adapters.outbound.readers.pdf_reader import PdfReader, ScannedPdf
from forms2json.application.ports.document_reader import ExtractionFailed
from forms2json.domain.document import Block, Checkbox, NormalizedDocument, Table, TextBlock
from forms2json.domain.upload import DOCX, PDF

DATA = Path(__file__).parents[3] / "data"


def read_form(pattern: str) -> NormalizedDocument:
    (path,) = DATA.glob(pattern)
    return PdfReader().read(path.read_bytes())


def all_blocks(document: NormalizedDocument) -> list[Block]:
    return [block for page in document.pages for block in page.blocks]


def scanned_pdf() -> bytes:
    """One page with a 1x1 inline image and no text, like a scanner output."""
    stream = b"q 100 0 0 100 0 0 cm BI /W 1 /H 1 /BPC 8 /CS /G ID \x80 EI Q"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
    ]
    pdf, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return pdf


def test_supports_only_pdf() -> None:
    assert PdfReader().supports(PDF)
    assert not PdfReader().supports(DOCX)


def test_pages_keep_their_numbers() -> None:
    document = read_form("9. */*.pdf")

    assert [page.number for page in document.pages] == list(range(1, 17))


def test_checkbox_glyphs_become_checkboxes_as_in_docx() -> None:
    blocks = all_blocks(read_form("9. */*.pdf"))

    checkboxes = [block for block in blocks if isinstance(block, Checkbox)]
    assert len(checkboxes) == 12
    assert Checkbox("adres siedziby klubu", checked=False) in checkboxes


def test_ruled_tables_are_read_once_in_reading_order() -> None:
    page = read_form("7. */*.PDF").pages[0]

    tables = [block for block in page.blocks if isinstance(block, Table)]
    assert tables[0].rows[0] == ("A", "DANE IDENTYFIKACYJNE WNIOSKODAWCY")
    assert ("Ulica:", "Nr domu:", "Nr lokalu:") in tables[0].rows
    # Text of the table is not repeated as free text, and the table sits below the title.
    assert TextBlock("Ulica:") not in page.blocks
    title = next(i for i, b in enumerate(page.blocks) if isinstance(b, TextBlock))
    assert title < page.blocks.index(tables[0])


def test_page_without_text_layer_needs_ocr() -> None:
    with pytest.raises(ScannedPdf, match="wymaga OCR"):
        PdfReader().read(scanned_pdf())


def test_too_many_pages_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_reader, "MAX_PAGES", 1)

    with pytest.raises(ExtractionFailed, match="za dużo stron"):
        read_form("1. */*.pdf")


def test_damaged_pdf_fails_with_extraction_failed() -> None:
    with pytest.raises(ExtractionFailed, match="uszkodzony"):
        PdfReader().read(b"%PDF-1.4\n" + b"\x00" * 64)
