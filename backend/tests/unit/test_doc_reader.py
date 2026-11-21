import time
from pathlib import Path

import pytest

from forms2json.adapters.outbound.readers.doc_reader import DocReader, soffice_to_docx
from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.application.ports.document_reader import ExtractionFailed
from forms2json.domain.document import TextBlock
from forms2json.domain.upload import DOC, DOCX, validate_upload

from .test_docx_reader import DATA, docx

DOCX_INSIDE = ["5. */*podatku.DOC", "7. */*agresywne.DOC"]


def test_reads_the_converted_docx() -> None:
    calls: list[tuple[bytes, float]] = []

    def convert(content: bytes, timeout: float) -> bytes:
        calls.append((content, timeout))
        return docx("<w:p><w:r><w:t>Wniosek</w:t></w:r></w:p>")

    document = DocReader(7.0, convert).read(b"doc bytes")

    assert calls == [(b"doc bytes", 7.0)]
    assert document.pages[0].blocks == (TextBlock("Wniosek"),)


def test_supports_only_doc() -> None:
    reader = DocReader(1.0)
    assert reader.supports(DOC)
    assert not reader.supports(DOCX)


@pytest.mark.parametrize("pattern", DOCX_INSIDE)
def test_doc_that_is_docx_inside_goes_to_the_docx_reader(pattern: str) -> None:
    (path,) = DATA.glob(pattern)
    content = path.read_bytes()

    assert validate_upload(path.name, content, len(content)) == DOCX
    assert DocxReader().read(content).pages[0].blocks


def fake_soffice(directory: Path, script: str, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = directory / "soffice"
    binary.write_text(f"#!/bin/sh\n{script}\n")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(directory))


def test_hanging_soffice_is_killed_after_the_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_soffice(tmp_path, "sleep 30", monkeypatch)
    started = time.monotonic()

    with pytest.raises(ExtractionFailed):
        soffice_to_docx(b"doc", 0.5)

    assert time.monotonic() - started < 5


@pytest.mark.parametrize("script", ["exit 1", "exit 0"])  # error, or no output file
def test_failed_conversion_raises_extraction_failed(
    script: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_soffice(tmp_path, script, monkeypatch)
    with pytest.raises(ExtractionFailed):
        soffice_to_docx(b"doc", 5)


def test_missing_soffice_raises_extraction_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(ExtractionFailed):
        soffice_to_docx(b"doc", 5)
