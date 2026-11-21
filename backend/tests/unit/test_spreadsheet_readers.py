import io
import zipfile
from pathlib import Path

import pytest

from forms2json.adapters.outbound.readers.ods_reader import OdsReader
from forms2json.adapters.outbound.readers.xlsx_reader import XlsxReader
from forms2json.application.ports.document_reader import DocumentReader
from forms2json.domain.document import NormalizedDocument, Table
from forms2json.domain.upload import ODS, XLSX

DATA_DIR = Path(__file__).parents[3] / "data"
STIPEND = next(DATA_DIR.glob("9.*")) / "Wniosek o przyznanie stypendium"
READERS = [(XlsxReader(), XLSX, ".xlsx"), (OdsReader(), ODS, ".ods")]


def _rows(document: NormalizedDocument, page: int) -> tuple[tuple[str, ...], ...]:
    block = document.pages[page].blocks[0]
    assert isinstance(block, Table)
    return block.rows


@pytest.mark.parametrize(("reader", "mime", "suffix"), READERS)
def test_reads_each_sheet_as_a_page_with_one_table(
    reader: DocumentReader, mime: str, suffix: str
) -> None:
    document = reader.read(STIPEND.with_suffix(suffix).read_bytes())

    assert reader.supports(mime)
    assert [page.number for page in document.pages] == [1, 2, 3, 4]
    # The merged title cell appears once, without the empty cells around it.
    assert _rows(document, 1)[0] == (
        "I.",
        "Wniosek o przyznanie stypendium sportowego Rady Miasta Zgierza",
    )


def test_xlsx_and_ods_of_the_same_form_read_the_same() -> None:
    xlsx = XlsxReader().read(STIPEND.with_suffix(".xlsx").read_bytes())
    ods = OdsReader().read(STIPEND.with_suffix(".ods").read_bytes())

    assert xlsx == ods


def test_readers_reject_other_types() -> None:
    assert not XlsxReader().supports(ODS)
    assert not OdsReader().supports(XLSX)


def _ods(sheets: str) -> bytes:
    content = (
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
        ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        f"<office:body><office:spreadsheet>{sheets}</office:spreadsheet></office:body>"
        "</office:document-content>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", ODS)
        archive.writestr("content.xml", content)
    return buffer.getvalue()


def test_ods_expands_repeats_keeps_spaces_and_skips_empty_sheets() -> None:
    content = _ods(
        '<table:table table:name="A">'
        '<table:table-row table:number-rows-repeated="1048000">'
        "<table:table-cell/></table:table-row>"
        '<table:table-row table:number-rows-repeated="2">'
        '<table:table-cell table:number-columns-spanned="2"><text:p>Imię<text:s text:c="2"/>i'
        "<text:span>nazwisko</text:span></text:p></table:table-cell>"
        "<table:covered-table-cell/>"
        '<table:table-cell table:number-columns-repeated="2"><text:p>x</text:p></table:table-cell>'
        "</table:table-row></table:table>"
        '<table:table table:name="B"/>'
    )

    document = OdsReader().read(content)

    assert _rows(document, 0) == (("Imię  inazwisko", "x", "x"),) * 2
    assert document.pages[1].blocks == ()
