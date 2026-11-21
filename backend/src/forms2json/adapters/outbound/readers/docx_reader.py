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
# Word content-control checkboxes render as these glyphs too, so one rule covers both;
# the PDF reader shares it (❑ is the Word-exported box in form 7).
BOX_STATES = {"☐": False, "□": False, "❑": False, "☒": True, "☑": True}
BOX_SPLIT = re.compile(f"([{''.join(BOX_STATES)}])")
# Squares of the Wingdings font table (byte -> glyph). Word keeps symbol-font text in the private
# use area (0xF000 + byte); other fonts give these codes other glyphs (Symbol 0x71 is θ).
WINGDINGS = "Wingdings"
WINGDINGS_BOXES = {0x6F: "☐", 0x71: "❑", 0x72: "❑", 0xA8: "☐", 0x78: "☒", 0xFD: "☒", 0xFE: "☑"}
BULLET = "• "
# Parts outside the body that still hold form text (a fee in the footer, footnote "dane
# nieobowiązkowe"). Read after the body, as the page layout that places them is not in the XML.
EXTRA_PARTS = re.compile(r"word/(header\d*|footer\d*)\.xml")
NOTE_PARTS = ("word/footnotes.xml", "word/endnotes.xml")
NOTE_REFERENCES = (f"{W}footnoteReference", f"{W}endnoteReference")

type Bullets = dict[tuple[str, str], str]  # (numId, ilvl) -> marker put before the item text


class DocxReader(DocumentReader):
    def supports(self, mime_type: str) -> bool:
        return mime_type == DOCX

    def read(self, content: bytes) -> NormalizedDocument:
        with open_archive(content) as archive:
            names = archive.namelist()
            body = ElementTree.fromstring(archive.read("word/document.xml"))
            numbering = "word/numbering.xml"
            bullets = (
                _bullets(ElementTree.fromstring(archive.read(numbering)))
                if numbering in names
                else {}
            )
            extras = [
                ElementTree.fromstring(archive.read(n))
                for n in sorted(names)
                if EXTRA_PARTS.fullmatch(n)
            ]
            notes = [ElementTree.fromstring(archive.read(n)) for n in NOTE_PARTS if n in names]
        blocks = list(_blocks(body, bullets))
        blocks.extend(note for part in notes for note in _notes(part))
        for part in extras:  # a header repeated per section is stored once per section
            blocks.extend(b for b in _blocks(part, bullets) if b not in blocks)
        # shortcut: DOCX has no fixed pages (the layout engine decides), so everything is page 1;
        # split on explicit page breaks when a later step needs pages.
        return NormalizedDocument(pages=(Page(number=1, blocks=tuple(blocks)),))


def _bullets(numbering: ElementTree.Element) -> Bullets:
    """Bullet list levels: a Wingdings square is a checkbox, any other bullet a plain list item."""
    levels: dict[str, dict[str, str]] = {}
    for abstract in numbering.iter(f"{W}abstractNum"):
        markers = levels.setdefault(abstract.get(f"{W}abstractNumId", ""), {})
        for level in abstract.iter(f"{W}lvl"):
            fmt, text = level.find(f"{W}numFmt"), level.find(f"{W}lvlText")
            if fmt is None or fmt.get(f"{W}val") != "bullet" or text is None:
                continue
            fonts = level.find(f"{W}rPr/{W}rFonts")
            font = fonts.get(f"{W}ascii", "") if fonts is not None else ""
            glyph = _symbols(text.get(f"{W}val", ""), font)
            box = next((c for c in glyph if c in BOX_STATES), None)
            markers[level.get(f"{W}ilvl", "0")] = f"{box} " if box else BULLET
    bullets: Bullets = {}
    for num in numbering.iter(f"{W}num"):
        abstract_id = num.find(f"{W}abstractNumId")
        if abstract_id is not None:
            for ilvl, marker in levels.get(abstract_id.get(f"{W}val", ""), {}).items():
                bullets[(num.get(f"{W}numId", ""), ilvl)] = marker
    return bullets


def _symbols(text: str, font: str) -> str:
    """Wingdings squares as Unicode boxes; the text of any other font is left as it is."""
    if font != WINGDINGS:
        return text
    return "".join(WINGDINGS_BOXES.get(ord(c) & 0xFF, c) if _symbol_code(c) else c for c in text)


def _symbol_code(char: str) -> bool:
    return ord(char) < 0x100 or 0xF000 <= ord(char) <= 0xF0FF


def _notes(part: ElementTree.Element) -> Iterator[Block]:
    """Footnotes and endnotes, tagged like their reference in the body ("[przypis 1]")."""
    for note in part:
        if note.get(f"{W}type"):  # separator and continuation notice, no content
            continue
        parts: list[str] = []
        _collect(note, parts, [])
        # The note repeats its mark, often followed by ")" written by hand.
        text = " ".join("".join(parts).split()).lstrip(").: ")
        if text:
            yield TextBlock(f"{_note_tag(note)} {text}")


def _note_tag(element: ElementTree.Element) -> str:
    return f"[przypis {element.get(f'{W}id', '')}]"


def _blocks(container: ElementTree.Element, bullets: Bullets) -> Iterator[Block]:
    for child in container:
        if child.tag == f"{W}p":
            yield from _paragraph(child, bullets)
        elif child.tag == f"{W}tbl":
            yield _table(child, bullets)
        else:  # body, content controls (sdt), customXml, footnotes and other wrappers
            yield from _blocks(child, bullets)


def _paragraph(paragraph: ElementTree.Element, bullets: Bullets) -> Iterator[Block]:
    parts: list[str] = []
    text_boxes: list[ElementTree.Element] = []
    _collect(paragraph, parts, text_boxes)
    text = "".join(parts)
    if text.strip():
        text = _marker(paragraph, bullets) + text.strip()
    head, *rest = BOX_SPLIT.split(text)
    if head.strip():
        yield TextBlock(head.strip())
    for box, label in batched(rest, 2, strict=True):
        yield Checkbox(label=label.strip(), checked=BOX_STATES[box])
    # shortcut: text boxes follow their anchor paragraph, not their position on the page;
    # sort by wp:positionV if Understand gets confused by PDF-converted forms (form 8).
    for text_box in text_boxes:
        yield from _blocks(text_box, bullets)


def _marker(paragraph: ElementTree.Element, bullets: Bullets) -> str:
    num_id = paragraph.find(f"{W}pPr/{W}numPr/{W}numId")
    if num_id is None:
        return ""
    ilvl = paragraph.find(f"{W}pPr/{W}numPr/{W}ilvl")
    level = ilvl.get(f"{W}val", "0") if ilvl is not None else "0"
    return bullets.get((num_id.get(f"{W}val", ""), level), "")


def _collect(
    element: ElementTree.Element, parts: list[str], text_boxes: list[ElementTree.Element]
) -> None:
    for child in element:
        if child.tag in (MC_FALLBACK, f"{W}pPr", f"{W}rPr"):  # pPr holds tab stops, not tabs
            continue
        if child.tag == f"{W}txbxContent":
            text_boxes.append(child)
            continue
        if child.tag == f"{W}r":
            fonts = child.find(f"{W}rPr/{W}rFonts")
            font = fonts.get(f"{W}ascii", "") if fonts is not None else ""
            run: list[str] = []
            _collect(child, run, text_boxes)
            parts.append(_symbols("".join(run), font))
            continue
        if child.tag == f"{W}t":
            parts.append(child.text or "")
        elif child.tag == f"{W}tab":
            parts.append("\t")
        elif child.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
        elif child.tag in NOTE_REFERENCES:
            parts.append(_note_tag(child))
        elif child.tag == f"{W}sym":  # symbol inserted with Insert > Symbol
            parts.append(
                _symbols(chr(int(child.get(f"{W}char", "0"), 16)), child.get(f"{W}font", ""))
            )
        elif child.tag == f"{W}checkBox":  # legacy form field (FORMCHECKBOX)
            parts.append("☒" if _legacy_checked(child) else "☐")
        _collect(child, parts, text_boxes)


def _legacy_checked(check_box: ElementTree.Element) -> bool:
    state = check_box.find(f"{W}checked")
    if state is None:
        state = check_box.find(f"{W}default")
    return state is not None and state.get(f"{W}val", "1") in ("1", "true", "on")


def _table(table: ElementTree.Element, bullets: Bullets) -> Table:
    # Cells are flattened to text, so nested tables and checkboxes inside cells stay readable.
    return Table(
        rows=tuple(
            tuple(
                "\n".join(_as_text(block) for block in _blocks(cell, bullets))
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
