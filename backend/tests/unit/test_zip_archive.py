import io
import zipfile

import pytest

from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.adapters.outbound.readers.ods_reader import OdsReader
from forms2json.adapters.outbound.readers.xlsx_reader import XlsxReader
from forms2json.adapters.outbound.readers.zip_archive import MAX_UNCOMPRESSED_BYTES
from forms2json.application.ports.document_reader import DocumentReader, ExtractionFailed

READERS = [DocxReader(), XlsxReader(), OdsReader()]


def zip_of(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


ODS_SHEET = (
    b'<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    b' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    b' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><table:table>'
    b'<table:table-row table:number-rows-repeated="many">'
    b"<table:table-cell><text:p>x</text:p></table:table-cell></table:table-row></table:table>"
    b"</office:document-content>"
)
DAMAGED = {
    "not a zip": b"PK\x03\x04garbage",
    "empty zip": zip_of({}),
    "broken xml": zip_of(
        {name: b"<broken" for name in ("word/document.xml", "content.xml", "[Content_Types].xml")}
    ),
}


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("content", DAMAGED.values(), ids=DAMAGED.keys())
def test_damaged_file_raises_extraction_failed(reader: DocumentReader, content: bytes) -> None:
    with pytest.raises(ExtractionFailed, match="uszkodzony"):
        reader.read(content)


def test_crafted_ods_attribute_raises_extraction_failed() -> None:
    with pytest.raises(ExtractionFailed):
        OdsReader().read(zip_of({"content.xml": ODS_SHEET}))


def test_ods_with_too_large_content_xml_is_rejected_before_decompression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # About 50 kB on disk, over the limit once inflated.
    bomb = zip_of({"content.xml": b" " * (MAX_UNCOMPRESSED_BYTES + 1)})

    def no_decompression(*_: object, **__: object) -> None:
        raise AssertionError("an entry was decompressed")

    monkeypatch.setattr(zipfile.ZipFile, "open", no_decompression)
    for reader in READERS:  # the check is shared, so the other formats reject it the same way
        with pytest.raises(ExtractionFailed, match="za duży"):
            reader.read(bomb)
