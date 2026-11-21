import re
import shutil
from pathlib import Path

import pytest

from forms2json.adapters.outbound.readers.doc_reader import DocReader
from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.domain.document import NormalizedDocument

DATA = Path(__file__).parents[3] / "data"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("soffice") is None, reason="needs LibreOffice (worker image)"),
]


def words(document: NormalizedDocument) -> set[str]:
    return set(re.findall(r"\w+", repr(document.pages)))


def test_real_doc_reads_like_its_docx_version() -> None:
    (doc,) = DATA.glob("3. */*.doc")
    (docx,) = DATA.glob("3. */*.docx")

    from_doc = words(DocReader(120).read(doc.read_bytes()))
    from_docx = words(DocxReader().read(docx.read_bytes()))

    assert len(from_doc & from_docx) > 0.9 * len(from_docx)
