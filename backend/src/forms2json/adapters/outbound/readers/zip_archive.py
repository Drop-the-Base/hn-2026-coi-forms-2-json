"""Shared guard for the ZIP-based formats (DOCX, XLSX, ODS) at the untrusted-file boundary."""

import io
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from xml.etree import ElementTree

from forms2json.application.ports.document_reader import ExtractionFailed

# Guards against ZIP bombs; the XML of a real form is a few MB at most. zipfile never
# inflates an entry past its declared file_size, so summing the declared sizes is enough.
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024

# What zipfile, zlib, ElementTree and openpyxl raise on a damaged or crafted file
# (RuntimeError: encrypted entry, NotImplementedError: unknown compression, KeyError: no entry).
_CORRUPT_FILE_ERRORS = (
    zipfile.BadZipFile,
    zlib.error,
    ElementTree.ParseError,
    KeyError,
    ValueError,
    RuntimeError,
    NotImplementedError,
    EOFError,
    OSError,
)


@contextmanager
def open_archive(content: bytes) -> Iterator[zipfile.ZipFile]:
    """Opens the ZIP after a size check; errors raised while reading it become ExtractionFailed."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(info.file_size for info in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                raise ExtractionFailed("Plik po rozpakowaniu jest za duży.")
            yield archive
    except ExtractionFailed:
        raise
    except _CORRUPT_FILE_ERRORS as error:
        raise ExtractionFailed("Plik jest uszkodzony albo ma nieprawidłową strukturę.") from error
