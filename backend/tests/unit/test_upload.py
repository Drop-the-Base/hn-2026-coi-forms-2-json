import io
import zipfile
from pathlib import Path

import pytest

from forms2json.domain.upload import (
    ALLOWED_TYPES_BY_EXTENSION,
    DOC,
    DOCX,
    JPEG,
    ODS,
    OLE2_SIGNATURE,
    PDF,
    PNG,
    XLSX,
    FileTooLarge,
    InvalidFileName,
    UnsupportedFileType,
    validate_upload,
)

MAX = 1024
DATA_DIR = Path(__file__).parents[3] / "data"


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


PDF_BYTES = b"%PDF-1.7\n"
DOC_BYTES = OLE2_SIGNATURE + b"\x00" * 8
DOCX_BYTES = _zip({"[Content_Types].xml": b"", "word/document.xml": b""})
XLSX_BYTES = _zip({"[Content_Types].xml": b"", "xl/workbook.xml": b""})
ODS_BYTES = _zip({"mimetype": ODS.encode(), "content.xml": b""})
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 8
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        ("a.pdf", PDF_BYTES, PDF),
        ("a.PDF", PDF_BYTES, PDF),
        ("a.doc", DOC_BYTES, DOC),
        ("a.DOC", DOCX_BYTES, DOCX),  # FR-03: .DOC that is DOCX inside
        ("a.docx", DOCX_BYTES, DOCX),
        ("a.xlsx", XLSX_BYTES, XLSX),
        ("a.ODS", ODS_BYTES, ODS),
        ("a.jpg", JPEG_BYTES, JPEG),
        ("a.JPEG", JPEG_BYTES, JPEG),
        ("a.Png", PNG_BYTES, PNG),
        ("Wniosek o zwrot - wersja (1).pdf", PDF_BYTES, PDF),
    ],
)
def test_accepts_supported_file(filename: str, content: bytes, expected: str) -> None:
    assert validate_upload(filename, content, MAX) == expected


def test_accepts_name_of_exactly_250_chars() -> None:
    assert validate_upload("a" * 246 + ".pdf", PDF_BYTES, MAX) == PDF


def test_rejects_name_longer_than_250_chars() -> None:
    with pytest.raises(InvalidFileName, match="za długa"):
        validate_upload("a" * 247 + ".pdf", PDF_BYTES, MAX)


@pytest.mark.parametrize("char", list(";:><\\/|'*%$"))
def test_rejects_forbidden_char_in_name(char: str) -> None:
    with pytest.raises(InvalidFileName, match="niedozwolone znaki"):
        validate_upload(f"wniosek{char}1.pdf", PDF_BYTES, MAX)


@pytest.mark.parametrize("filename", ["a.txt", "a.exe", "a.jpe", "pdf", ".pdf", "a.pdf.zip", ""])
def test_rejects_unsupported_extension(filename: str) -> None:
    with pytest.raises(UnsupportedFileType, match="Nieobsługiwany format"):
        validate_upload(filename, PDF_BYTES, MAX)


def test_rejects_file_over_size_limit() -> None:
    with pytest.raises(FileTooLarge, match="za duży"):
        validate_upload("a.pdf", PDF_BYTES + b"\x00" * MAX, MAX)


def test_accepts_file_exactly_at_size_limit() -> None:
    assert validate_upload("a.pdf", PDF_BYTES.ljust(MAX, b"\x00"), MAX) == PDF


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("a.pdf", PNG_BYTES),
        ("a.png", JPEG_BYTES),
        ("a.jpg", PDF_BYTES),
        ("a.docx", DOC_BYTES),  # DOC disguised as DOCX is not accepted, only the reverse
        ("a.docx", XLSX_BYTES),
        ("a.xlsx", ODS_BYTES),
        ("a.ods", DOCX_BYTES),
        ("a.doc", XLSX_BYTES),
        ("a.docx", _zip({"other.txt": b""})),
        ("a.docx", b"PK\x03\x04 broken zip"),
        ("a.pdf", b""),
        ("a.pdf", b"<html>%PDF-</html>"),
    ],
)
def test_rejects_content_not_matching_extension(filename: str, content: bytes) -> None:
    with pytest.raises(UnsupportedFileType, match="nie odpowiada rozszerzeniu"):
        validate_upload(filename, content, MAX)


SAMPLES = sorted(
    path
    for path in DATA_DIR.rglob("*")
    if path.is_file() and path.suffix.lower() in ALLOWED_TYPES_BY_EXTENSION
)


@pytest.mark.parametrize("path", SAMPLES, ids=lambda path: path.name)
def test_accepts_every_dataset_sample(path: Path) -> None:
    validate_upload(path.name, path.read_bytes(), 100 * 1024 * 1024)
