import io
import zipfile

from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.domain.document import Table, TextBlock

NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
)
EMU = 12700


def box(x: float, y: float, w: float, h: float, text: str = "") -> str:
    """A page-anchored shape (text box, or a drawn square when text is empty) at points x, y."""
    content = (
        f"<w:txbxContent><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:txbxContent>" if text else ""
    )
    h_pos, v_pos = (
        f'<wp:position{axis} relativeFrom="page"><wp:posOffset>{int(v * EMU)}</wp:posOffset>'
        f"</wp:position{axis}>"
        for axis, v in (("H", x), ("V", y))
    )
    extent = f'<wp:extent cx="{int(w * EMU)}" cy="{int(h * EMU)}"/>'
    return (
        f"<w:r><w:drawing><wp:anchor>{h_pos}{v_pos}{extent}{content}</wp:anchor></w:drawing></w:r>"
    )


def positioned_docx(shapes: list[str]) -> bytes:
    filler = [box(10, 800 + i, 20, 1, "") for i in range(20)]  # thin lines: enough anchors, no text
    body = "<w:p>" + "".join(shapes + filler) + "</w:p>"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml", f"<w:document {NS}><w:body>{body}</w:body></w:document>"
        )
    return buffer.getvalue()


def test_converted_pdf_is_read_by_position_and_broken_cells_are_joined() -> None:
    content = positioned_docx(
        [
            box(50, 100, 200, 10, "36. Liczba gospodarstw"),
            box(300, 100, 150, 10, "38. Wysokość opłaty"),
            box(50, 112, 200, 10, "nie przekraczającej 45 m²"),  # continues the cell above
            box(260, 112, 8, 10, "X"),
            box(280, 112, 30, 10, "38 zł"),
            box(330, 112, 80, 10, "zł"),
            box(50, 140, 10, 10),  # drawn square = check box
            box(65, 140, 100, 10, "TAK"),
        ]
    )

    (page,) = DocxReader().read(content).pages
    assert page.blocks == (
        Table(
            rows=(
                (
                    "36. Liczba gospodarstw nie przekraczającej 45 m²",
                    "X",
                    "38 zł",
                    "38. Wysokość opłaty zł",
                ),
            )
        ),
        TextBlock("☐ TAK"),
    )
