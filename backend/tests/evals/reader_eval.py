"""Reader quality without the LLM: the PDF of the same form is the reference (#136, FR-07).

uv run python -m tests.evals.reader_eval --name czytnik-1 [--baseline czytnik-0]   (in backend/)

Every form in data/ comes in several formats exported from one source, and its PDF shows all the
text a citizen sees (footers and footnotes included). For the DOCX of each form it reports:
- coverage: share of the PDF's words (3+ letters) that reach the text sent to the model,
- checkboxes read by the reader vs. squares in the PDF (small square rectangles and box glyphs),
- list items and footnotes the reader marks.
Coverage checks presence, not order or which field a word belongs to.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from forms2json.adapters.outbound.readers.docx_reader import (
    BOX_STATES,
    BULLET,
    WINGDINGS,
    WINGDINGS_BOXES,
    DocxReader,
)
from forms2json.application.pipeline.understand_step import serialize
from forms2json.domain.document import Checkbox, Table

DATA = Path(__file__).parents[3] / "data"
RUNS = Path(__file__).parent / "runs"
WORD = re.compile(r"[^\W\d_]{3,}|\d{3,}")
FOOTNOTE = re.compile(r"\[przypis \d+\]")
# A drawn checkbox: a square a few points wide (a text line is ~10 pt high).
BOX_SIZE = (5, 16)
BOX_TOLERANCE = 2

COLUMNS = [
    ("pokrycie PDF", "coverage", "{:.1%}"),
    ("kratki", "checkboxes", "{:.0f}"),
    ("kratki w PDF", "pdf_checkboxes", "{:.0f}"),
    ("listy", "list_items", "{:.0f}"),
    ("przypisy", "footnotes", "{:.0f}"),
]

type Row = dict[str, Any]


def docx_file(directory: Path) -> Path | None:
    """The form's DOCX; a .doc that is a DOCX inside (FR-03) counts too."""
    files = sorted(f for f in directory.iterdir() if "wizualizacja" not in f.name)
    docx = [f for f in files if f.suffix.lower() == ".docx"]
    doc = [f for f in files if f.suffix.lower() == ".doc" and f.read_bytes()[:2] == b"PK"]
    return next(iter(docx + doc), None)


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def coverage(reference: str, text: str) -> tuple[float, list[str]]:
    """Share of the reference words found in the text, and the missing ones."""
    expected = words(reference)
    missing = sorted(expected - words(text))
    return (1 - len(missing) / len(expected) if expected else 1.0), missing


def pdf_reference(path: Path) -> tuple[str, int]:
    """The PDF's text and the number of checkboxes drawn or typed in it."""
    texts, boxes = [], 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            boxes += sum(_is_box(r["width"], r["height"]) for r in page.rects)
            boxes += sum(_is_box_glyph(c["text"], c["fontname"]) for c in page.chars)
    return "\n".join(texts), boxes


def _is_box(width: float, height: float) -> bool:
    return BOX_SIZE[0] <= width <= BOX_SIZE[1] and abs(width - height) <= BOX_TOLERANCE


def _is_box_glyph(char: str, font: str) -> bool:
    code = ord(char) if len(char) == 1 else 0
    return char in BOX_STATES or (WINGDINGS in font and (code & 0xFF) in WINGDINGS_BOXES)


def measure(directory: Path) -> Row | None:
    source = docx_file(directory)
    pdf = next((f for f in sorted(directory.iterdir()) if f.suffix.lower() == ".pdf"), None)
    if source is None or pdf is None:
        return None
    document = DocxReader().read(source.read_bytes())
    text = serialize(document)
    blocks = [block for page in document.pages for block in page.blocks]
    cells = "".join(c for b in blocks if isinstance(b, Table) for row in b.rows for c in row)
    reference, pdf_boxes = pdf_reference(pdf)
    share, missing = coverage(reference, text)
    return {
        "coverage": share,
        "checkboxes": sum(isinstance(b, Checkbox) for b in blocks)
        + sum(cells.count(box) for box in BOX_STATES),
        "pdf_checkboxes": pdf_boxes,
        "list_items": text.count(BULLET),
        "footnotes": len(set(FOOTNOTE.findall(text))),
        "missing": missing,
    }


def to_markdown(rows: dict[str, Row], baseline: dict[str, Row] | None = None) -> str:
    lines = [
        "| formularz | " + " | ".join(h for h, _, _ in COLUMNS) + " | brakujące słowa (próbka) |",
        "|---" * (len(COLUMNS) + 2) + "|",
    ]
    for name, row in rows.items():
        cells = [name]
        for _, key, fmt in COLUMNS:
            cell = fmt.format(row[key])
            before = (baseline or {}).get(name, {}).get(key)
            if before is not None and before != row[key]:
                cell = f"{fmt.format(before)} → {cell}"
            cells.append(cell)
        cells.append(", ".join(row["missing"][:8]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="zapisz przebieg w runs/<name>/reader.json")
    parser.add_argument("--baseline", help="nazwa zapisanego przebiegu z runs/")
    args = parser.parse_args()

    rows = {}
    for directory in sorted(DATA.glob("[1-9]. *")):
        row = measure(directory)
        if row is not None:
            rows[directory.name.split(".")[0]] = row
    baseline = None
    if args.baseline:
        baseline = json.loads((RUNS / args.baseline / "reader.json").read_text(encoding="utf-8"))
    if args.name:
        (RUNS / args.name).mkdir(parents=True, exist_ok=True)
        (RUNS / args.name / "reader.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    print(to_markdown(rows, baseline))


if __name__ == "__main__":
    main()
