"""Validation of an uploaded file before it enters the pipeline (FR-02..FR-05)."""

import io
import zipfile
from pathlib import PurePath

PDF = "application/pdf"
DOC = "application/msword"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ODS = "application/vnd.oasis.opendocument.spreadsheet"
JPEG = "image/jpeg"
PNG = "image/png"

# The dataset has .DOC files that are DOCX inside (FR-03), so .doc accepts both.
ALLOWED_TYPES_BY_EXTENSION = {
    ".pdf": {PDF},
    ".doc": {DOC, DOCX},
    ".docx": {DOCX},
    ".ods": {ODS},
    ".xlsx": {XLSX},
    ".jpg": {JPEG},
    ".jpeg": {JPEG},
    ".png": {PNG},
}

MAX_NAME_LENGTH = 250
FORBIDDEN_NAME_CHARS = frozenset(";:><\\/|'*%$")

OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class InvalidUpload(ValueError):
    """The uploaded file is rejected; the message is shown to the user (Polish)."""


class InvalidFileName(InvalidUpload):
    pass


class FileTooLarge(InvalidUpload):
    pass


class UnsupportedFileType(InvalidUpload):
    pass


def validate_upload(filename: str, content: bytes, max_bytes: int) -> str:
    """Checks name, extension, size and content; returns the MIME type detected from content."""
    if len(filename) > MAX_NAME_LENGTH:
        raise InvalidFileName(f"Nazwa pliku jest za długa (maks. {MAX_NAME_LENGTH} znaków).")
    forbidden = sorted(FORBIDDEN_NAME_CHARS.intersection(filename))
    if forbidden:
        raise InvalidFileName(f"Nazwa pliku zawiera niedozwolone znaki: {' '.join(forbidden)}")

    extension = PurePath(filename).suffix.lower()
    allowed = ALLOWED_TYPES_BY_EXTENSION.get(extension)
    if allowed is None:
        supported = ", ".join(ALLOWED_TYPES_BY_EXTENSION)
        raise UnsupportedFileType(
            f"Nieobsługiwany format pliku. Dozwolone rozszerzenia: {supported}."
        )

    if len(content) > max_bytes:
        raise FileTooLarge(f"Plik jest za duży (maks. {max_bytes} bajtów).")

    detected = detect_mime_type(content)
    if detected not in allowed:
        raise UnsupportedFileType(
            f"Zawartość pliku nie odpowiada rozszerzeniu {extension} albo plik jest uszkodzony."
        )
    return detected


def detect_mime_type(content: bytes) -> str | None:
    """Recognises the supported formats by their byte signatures, without trusting the name."""
    if content.startswith(b"%PDF-"):
        return PDF
    if content.startswith(b"\xff\xd8\xff"):
        return JPEG
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if content.startswith(OLE2_SIGNATURE):
        # shortcut: any OLE2 container counts as DOC (an .xls renamed to .doc passes),
        # parse the CFB directory if the DOC reader starts failing on such files.
        return DOC
    if content.startswith(b"PK\x03\x04"):
        return _detect_zip_document(content)
    return None


def _detect_zip_document(content: bytes) -> str | None:
    # Reads only the central directory and the tiny ODF "mimetype" entry: no decompression bomb.
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "mimetype" in names:
                with archive.open("mimetype") as entry:
                    if entry.read(len(ODS) + 1) == ODS.encode():
                        return ODS
            if "word/document.xml" in names:
                return DOCX
            if "xl/workbook.xml" in names:
                return XLSX
    except zipfile.BadZipFile, OSError, RuntimeError, ValueError, NotImplementedError:
        return None
    return None
