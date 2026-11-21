"""DOCX reader on the standard library: WordprocessingML is plain XML in a ZIP."""

import re
from collections.abc import Iterator
from itertools import batched
from xml.etree import ElementTree

from forms2json.adapters.outbound.readers.zip_archive import open_archive
from forms2json.application.ports.document_reader import DocumentReader
from forms2json.domain.document import Block, Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.upload import DOCX

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# Text boxes are stored twice: as DrawingML and as a VML fallback; read only the first.
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
# Word content-control checkboxes render as these glyphs too, so one rule covers both.
BOX_STATES = {"☐": False, "□": False, "☒": True, "☑": True}
BOX_SPLIT = re.compile(f"([{''.join(BOX_STATES)}])")


class DocxReader(DocumentReader):
    def supports(self, mime_type: str) -> bool:
        return mime_type == DOCX

    def read(self, content: bytes) -> NormalizedDocument:
        with open_archive(content) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        # shortcut: DOCX has no fixed pages (the layout engine decides), so everything is page 1;
        # split on explicit page breaks when a later step needs pages.
        return NormalizedDocument(pages=(Page(number=1, blocks=tuple(_blocks(root))),))


def _blocks(container: ElementTree.Element) -> Iterator[Block]:
    for child in container:
        if child.tag == f"{W}p":
            yield from _paragraph(child)
        elif child.tag == f"{W}tbl":
            yield _table(child)
        else:  # body, content controls (sdt), customXml and other wrappers
            yield from _blocks(child)


def _paragraph(paragraph: ElementTree.Element) -> Iterator[Block]:
    parts: list[str] = []
    text_boxes: list[ElementTree.Element] = []
    _collect(paragraph, parts, text_boxes)
    head, *rest = BOX_SPLIT.split("".join(parts))
    if head.strip():
        yield TextBlock(head.strip())
    for box, label in batched(rest, 2, strict=True):
        yield Checkbox(label=label.strip(), checked=BOX_STATES[box])
    # shortcut: text boxes follow their anchor paragraph, not their position on the page;
    # sort by wp:positionV if Understand gets confused by PDF-converted forms (form 8).
    for text_box in text_boxes:
        yield from _blocks(text_box)


def _collect(
    element: ElementTree.Element, parts: list[str], text_boxes: list[ElementTree.Element]
) -> None:
    for child in element:
        if child.tag in (MC_FALLBACK, f"{W}pPr", f"{W}rPr"):  # pPr holds tab stops, not tabs
            continue
        if child.tag == f"{W}txbxContent":
            text_boxes.append(child)
            continue
        if child.tag == f"{W}t":
            parts.append(child.text or "")
        elif child.tag == f"{W}tab":
            parts.append("\t")
        elif child.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
        elif child.tag == f"{W}checkBox":  # legacy form field (FORMCHECKBOX)
            parts.append("☒" if _legacy_checked(child) else "☐")
        _collect(child, parts, text_boxes)


def _legacy_checked(check_box: ElementTree.Element) -> bool:
    state = check_box.find(f"{W}checked")
    if state is None:
        state = check_box.find(f"{W}default")
    return state is not None and state.get(f"{W}val", "1") in ("1", "true", "on")


def _table(table: ElementTree.Element) -> Table:
    # Cells are flattened to text, so nested tables and checkboxes inside cells stay readable.
    return Table(
        rows=tuple(
            tuple(
                "\n".join(_as_text(block) for block in _blocks(cell))
                for cell in row.findall(f"{W}tc")
            )
            for row in table.findall(f"{W}tr")
        )
    )


def _as_text(block: Block) -> str:
    match block:
        case TextBlock(text):
            return text
        case Checkbox(label, checked):
            return f"{'☒' if checked else '☐'} {label}"
        case Table(rows):
            return "\n".join(" | ".join(row) for row in rows)
