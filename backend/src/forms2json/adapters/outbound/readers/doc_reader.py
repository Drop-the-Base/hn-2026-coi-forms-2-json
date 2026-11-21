"""Old binary DOC: LibreOffice headless converts it to DOCX, then the DOCX reader reads it.

LibreOffice runs as an unmodified program, never linked (ADR-0013). A .doc that is DOCX inside
is detected as DOCX on upload, so it goes straight to DocxReader (FR-03).
"""

import os
import signal
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.application.ports.document_reader import DocumentReader, ExtractionFailed
from forms2json.domain.document import NormalizedDocument
from forms2json.domain.upload import DOC

FAILED = "Nie udało się przekonwertować pliku DOC (plik uszkodzony albo konwersja trwała za długo)."


def soffice_to_docx(content: bytes, timeout_seconds: float) -> bytes:
    # Files and the soffice profile live only in a temp dir on tmpfs, removed always (NFR-06).
    with tempfile.TemporaryDirectory(prefix="forms2json-doc-") as work:
        source = Path(work, "input.doc")
        source.write_bytes(content)
        command = [
            "soffice",
            f"-env:UserInstallation={Path(work, 'profile').as_uri()}",
            "--headless",
            "--norestore",
            "--convert-to",
            "docx",
            "--outdir",
            work,
            str(source),
        ]
        try:
            # Own session: on timeout kill the whole group, soffice.bin too, not only the wrapper.
            with subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "HOME": work},
                start_new_session=True,
            ) as process:
                try:
                    returncode = process.wait(timeout_seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    raise ExtractionFailed(FAILED) from None
            if returncode != 0:
                raise ExtractionFailed(FAILED)
            return Path(work, "input.docx").read_bytes()
        except OSError as error:  # soffice missing or no output file
            raise ExtractionFailed(FAILED) from error


class DocReader(DocumentReader):
    def __init__(
        self,
        timeout_seconds: float,
        convert: Callable[[bytes, float], bytes] = soffice_to_docx,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._convert = convert
        self._docx = DocxReader()

    def supports(self, mime_type: str) -> bool:
        return mime_type == DOC

    def read(self, content: bytes) -> NormalizedDocument:
        return self._docx.read(self._convert(content, self._timeout_seconds))
