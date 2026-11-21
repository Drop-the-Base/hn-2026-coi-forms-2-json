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


NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def docx(body: str, **parts: str) -> bytes:
    """A DOCX with this body; `parts` maps a part name (footer1, numbering...) to its XML."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml", f"<w:document {NS}><w:body>{body}</w:body></w:document>"
        )
        for name, xml in parts.items():
            archive.writestr(f"word/{name}.xml", xml)
    return buffer.getvalue()


def bullet_list(glyph: str, font: str) -> str:
    """numbering.xml with list numId=1 whose level 0 is a bullet `glyph` in `font`."""
    return (
        f'<w:numbering {NS}><w:abstractNum w:abstractNumId="7"><w:lvl w:ilvl="0">'
        f'<w:numFmt w:val="bullet"/><w:lvlText w:val="{glyph}"/>'
        f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}"/></w:rPr></w:lvl></w:abstractNum>'
        '<w:num w:numId="1"><w:abstractNumId w:val="7"/></w:num></w:numbering>'
    )


def list_item(text: str) -> str:
    return (
        '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        f"<w:r><w:t>{text}</w:t></w:r></w:p>"
    )


def test_supports_only_docx() -> None:
    assert DocxReader().supports(DOCX)
    assert not DocxReader().supports(PDF)


def test_checkbox_glyphs_split_a_paragraph_into_label_and_options() -> None:
    blocks = read_form("9. */Wniosek o przyznanie stypendium.docx")

    checkboxes = [block for block in blocks if isinstance(block, Checkbox)]
    assert len(checkboxes) == 12
    assert not any(box.checked for box in checkboxes)
    question = blocks.index(
        TextBlock("• Poczta tradycyjna - na który adres kierować korespondencję")
    )
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


def test_wingdings_squares_in_text_and_symbols_are_checkboxes() -> None:
    wingdings = '<w:rPr><w:rFonts w:ascii="Wingdings" w:hAnsi="Wingdings"/></w:rPr>'
    blocks = read_blocks(
        docx(
            f"<w:p><w:r>{wingdings}<w:t>\uf071</w:t></w:r><w:r><w:t> tak </w:t></w:r>"
            f"<w:r>{wingdings}<w:t>\uf0fe</w:t></w:r><w:r><w:t> nie</w:t></w:r></w:p>"
            '<w:p><w:r><w:sym w:font="Wingdings" w:char="F06F"/><w:t> może</w:t></w:r></w:p>'
        )
    )

    assert blocks == (
        Checkbox("tak", checked=False),
        Checkbox("nie", checked=True),
        Checkbox("może", checked=False),
    )


def test_same_code_in_another_font_is_not_a_checkbox() -> None:
    # 0xF071 is θ in the Symbol font: only the Wingdings table makes it a box.
    symbol = '<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol"/></w:rPr>'
    blocks = read_blocks(
        docx(f"<w:p><w:r>{symbol}<w:t>\uf071</w:t></w:r><w:r><w:t> kąt</w:t></w:r></w:p>")
    )

    assert not any(isinstance(block, Checkbox) for block in blocks)


def test_wingdings_square_bullet_makes_list_items_checkboxes() -> None:
    blocks = read_blocks(
        docx(
            list_item("gotówka") + list_item("przelew"),
            numbering=bullet_list("\uf06f", "Wingdings"),
        )
    )

    assert blocks == (Checkbox("gotówka", checked=False), Checkbox("przelew", checked=False))


def test_other_bullets_mark_list_items() -> None:
    blocks = read_blocks(
        docx(
            list_item("pierwsza") + "<w:p><w:r><w:t>bez listy</w:t></w:r></w:p>",
            numbering=bullet_list("\uf0b7", "Symbol"),
        )
    )

    assert blocks == (TextBlock("• pierwsza"), TextBlock("bez listy"))


def test_footer_and_header_text_follows_the_body_once() -> None:
    footer = f"<w:ftr {NS}><w:p><w:r><w:t>Opłata: 10 zł</w:t></w:r></w:p></w:ftr>"
    blocks = read_blocks(
        docx("<w:p><w:r><w:t>Treść</w:t></w:r></w:p>", footer1=footer, footer2=footer)
    )

    assert blocks == (TextBlock("Treść"), TextBlock("Opłata: 10 zł"))


def test_footnote_is_tagged_at_its_reference_and_after_the_body() -> None:
    footnotes = (
        f'<w:footnotes {NS}><w:footnote w:type="separator" w:id="-1">'
        "<w:p><w:r><w:separator/></w:r></w:p></w:footnote>"
        '<w:footnote w:id="1"><w:p><w:r><w:footnoteRef/></w:r>'
        "<w:r><w:t>) Dane nieobowiązkowe.</w:t></w:r></w:p></w:footnote></w:footnotes>"
    )
    body = '<w:p><w:r><w:t>Ulica</w:t></w:r><w:r><w:footnoteReference w:id="1"/></w:r></w:p>'
    blocks = read_blocks(docx(body, footnotes=footnotes))

    assert blocks == (TextBlock("Ulica[przypis 1]"), TextBlock("[przypis 1] Dane nieobowiązkowe."))
