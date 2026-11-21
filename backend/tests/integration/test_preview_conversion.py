import shutil
from pathlib import Path

import pytest

from forms2json.adapters.outbound.preview.libreoffice_pdf_renderer import LibreOfficePdfRenderer
from forms2json.domain.upload import validate_upload

DATA = Path(__file__).parents[3] / "data"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("soffice") is None, reason="needs LibreOffice (api image)"),
]


@pytest.mark.parametrize("pattern", ["3. */*.doc", "3. */*.docx", "3. */*.xlsx", "3. */*.ods"])
def test_real_office_file_renders_as_pdf(pattern: str) -> None:
    (path,) = DATA.glob(pattern)
    content = path.read_bytes()
    mime_type = validate_upload(path.name, content, len(content))

    pdf = LibreOfficePdfRenderer(120).render(content, mime_type)

    assert pdf.startswith(b"%PDF-")
