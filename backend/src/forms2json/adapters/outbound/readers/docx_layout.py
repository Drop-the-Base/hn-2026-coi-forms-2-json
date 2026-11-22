"""DOCX made of page-anchored text boxes (a PDF converted to Word), read by position.

Such a file has no tables: every word sits in a text box anchored to the page, table borders are
drawn lines and check boxes are drawn squares. Word places them by coordinates, so do we:
page = section, line = boxes whose vertical centres meet, cells = boxes left to right, a small
empty square = "☐" before the text on its right. A line starting lowercase continues the cells
above it, so a table cell broken over several lines is read as one cell.
"""

import re
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from forms2json.domain.document import Block, NormalizedDocument, Page, Table, TextBlock

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}
W = f"{{{NS['w']}}}"
EMU_PER_PT = 12700
MIN_BOXES = 20  # fewer page-anchored boxes: an ordinary document with a few floating shapes
CHECKBOX_PT = (5, 16)  # side of a drawn check box, points
ROW_TOLERANCE = 0.5  # boxes are one line when their centres are within half the shorter height
WORD_GAP_PT = 6  # a smaller horizontal gap is a space inside one cell, not a new cell
WORD_START = re.compile(r"^[a-ząćęłńóśźż(]")  # a cell continuing the text of the cell above
# A line starting with a lone operator (X, multiplication sign, =) continues a calculation row.
OPERATOR = re.compile("^[X\\u00d7=]$")


@dataclass
class _Box:
    page: int
    x: float
    y: float
    w: float
    h: float
    text: str  # "" for a check box

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class _Cell:
    x0: float
    x1: float
    text: str


def is_positioned(body: Element) -> bool:
    """A converted-PDF layout: no table and many text boxes anchored to the page."""
    if body.find(".//w:tbl", NS) is not None:
        return False
    anchors = body.findall(".//wp:anchor/wp:positionV[@relativeFrom='page']", NS)
    return len(anchors) >= MIN_BOXES


def read(body: Element) -> NormalizedDocument:
    boxes = _boxes(body)
    pages = []
    for number in sorted({b.page for b in boxes}):
        lines = [c for c in map(_cells, _lines([b for b in boxes if b.page == number])) if c]
        blocks: list[Block] = []
        for cells in _merge_continuations(lines):
            if len(cells) == 1:
                blocks.append(TextBlock(cells[0].text))
            else:
                blocks.append(Table(rows=(tuple(c.text for c in cells),)))
        pages.append(Page(number=number, blocks=tuple(blocks)))
    return NormalizedDocument(pages=tuple(pages))


def _boxes(body: Element) -> list[_Box]:
    out: list[_Box] = []
    page = 1
    for para in body.iter(W + "p"):
        # mc:Fallback repeats every shape as VML: only the modern drawing is read
        anchors = para.findall(".//mc:Choice//wp:anchor", NS)
        anchors += para.findall("./w:r/w:drawing/wp:anchor", NS)
        for anchor in anchors:
            x = int(anchor.findtext("wp:positionH/wp:posOffset", "0", NS)) / EMU_PER_PT
            y = int(anchor.findtext("wp:positionV/wp:posOffset", "0", NS)) / EMU_PER_PT
            ext = anchor.find("wp:extent", NS)
            w = int(ext.get("cx", "0")) / EMU_PER_PT if ext is not None else 0
            h = int(ext.get("cy", "0")) / EMU_PER_PT if ext is not None else 0
            content = anchor.find(".//w:txbxContent", NS)
            if content is not None:
                lines = [
                    "".join(t.text or "" for t in p.iter(W + "t")) for p in content.iter(W + "p")
                ]
                text = " ".join(" ".join(lines).split())
                if text:
                    out.append(_Box(page, x, y, w, h, text))
            elif CHECKBOX_PT[0] <= w <= CHECKBOX_PT[1] and abs(w - h) < 2:
                out.append(_Box(page, x, y, w, h, ""))
        if (
            para.find("w:pPr/w:sectPr", NS) is not None
        ):  # the paragraph closing a section ends a page
            page += 1
    return out


def _lines(page_boxes: list[_Box]) -> list[list[_Box]]:
    result: list[list[_Box]] = []
    for b in sorted(page_boxes, key=lambda b: (b.cy, b.x)):
        if result:
            last = result[-1]
            ref = min(last, key=lambda o: abs(o.cy - b.cy))
            if abs(ref.cy - b.cy) <= ROW_TOLERANCE * min(ref.h, b.h) + 1:
                last.append(b)
                continue
        result.append([b])
    return [sorted(r, key=lambda b: b.x) for r in result]


def _cells(line: list[_Box]) -> list[_Cell]:
    cells: list[_Cell] = []
    pending_box = False
    prev: _Box | None = None
    for b in line:
        if not b.text:
            pending_box, prev = True, None
            continue
        if prev is not None and b.x - (prev.x + prev.w) < WORD_GAP_PT and not pending_box:
            cells[-1].text += " " + b.text
            cells[-1].x1 = b.x + b.w
        else:
            cells.append(_Cell(b.x, b.x + b.w, ("☐ " if pending_box else "") + b.text))
        pending_box, prev = False, b
    return cells


def _merge_continuations(lines: list[list[_Cell]]) -> list[list[_Cell]]:
    """A line starting lowercase (or with a lone X / =) continues the line above: its word cells
    join the cell above they overlap most, the rest (X, =, amounts) are inserted in x order."""
    out: list[list[_Cell]] = []
    for cells in lines:
        if out and (WORD_START.match(cells[0].text) or OPERATOR.match(cells[0].text)):
            above = out[-1]
            for c in cells:
                best = max(above, key=lambda a: _overlap(a, c))
                if WORD_START.match(c.text) and _overlap(best, c) > 0:
                    best.text += " " + c.text
                    best.x0, best.x1 = min(best.x0, c.x0), max(best.x1, c.x1)
                else:
                    above.append(c)
                    above.sort(key=lambda a: a.x0)
            continue
        out.append(cells)
    return out


def _overlap(a: _Cell, b: _Cell) -> float:
    return min(a.x1, b.x1) - max(a.x0, b.x0)
