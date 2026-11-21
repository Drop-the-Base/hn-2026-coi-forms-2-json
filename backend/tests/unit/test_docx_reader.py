import io
import zipfile
from pathlib import Path

from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.domain.document import Block, Checkbox, Table, TextBlock
from forms2json.domain.upload import DOCX, PDF

DATA = Path(__file__).parents[3] / "data"


def read_blocks(content: bytes) -> tuple[Block, ...]:
    document = DocxReader().read(content)
    assert len(document.pages) == 1
    return document.pages[0].blocks


def read_form(pattern: str) -> tuple[Block, ...]:
    (path,) = DATA.glob(pattern)
    return read_blocks(path.read_bytes())


def docx(body: str) -> bytes:
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def test_supports_only_docx() -> None:
    assert DocxReader().supports(DOCX)
    assert not DocxReader().supports(PDF)


def test_checkbox_glyphs_split_a_paragraph_into_label_and_options() -> None:
    blocks = read_form("9. */Wniosek o przyznanie stypendium.docx")

    checkboxes = [block for block in blocks if isinstance(block, Checkbox)]
    assert len(checkboxes) == 12
    assert not any(box.checked for box in checkboxes)
    question = blocks.index(TextBlock("Poczta tradycyjna - na który adres kierować korespondencję"))
    assert blocks[question + 1] == Checkbox("adres siedziby klubu", checked=False)


def test_tables_keep_rows_and_cells() -> None:
    # The .DOC in the dataset is a DOCX inside (FR-03).
    blocks = read_form("7. */*.DOC")

    tables = [block for block in blocks if isinstance(block, Table)]
    assert len(tables) == 2
    assert tables[0].rows[0] == ("A", "DANE IDENTYFIKACYJNE WNIOSKODAWCY")
    assert tables[0].rows[2] == ("Ulica:", "Nr domu:", "Nr lokalu:")


def test_text_boxes_are_read_once_without_the_vml_fallback() -> None:
    blocks = read_form("2. */*.docx")

    assert blocks.count(TextBlock("Wniosek o zwrot opłaty skarbowej")) == 1


def test_checked_states_of_glyphs_and_legacy_form_fields() -> None:
    blocks = read_blocks(
        docx(
            '<w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="100"/></w:tabs></w:pPr>'
            "<w:r><w:t>Zgoda ☒ tak ☐ nie</w:t></w:r></w:p>"
            '<w:p><w:r><w:fldChar w:fldCharType="begin"><w:ffData><w:checkBox>'
            '<w:default w:val="0"/><w:checked/></w:checkBox></w:ffData></w:fldChar></w:r>'
            "<w:r><w:t>RODO</w:t></w:r></w:p>"
        )
    )

    assert blocks == (
        TextBlock("Zgoda"),
        Checkbox("tak", checked=True),
        Checkbox("nie", checked=False),
        Checkbox("RODO", checked=True),
    )
