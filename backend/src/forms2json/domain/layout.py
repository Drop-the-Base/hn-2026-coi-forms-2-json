"""Grid layout, ids and techNames (FR-08, K-14), with the rules read from references 1 and 5.

References put every element at x=0 across the full grid width (cols=3), whatever its type, so
there is no per-type width. A field takes one row and its y is its index in the section; a section
takes one header row plus one row per field and sits right below the previous section.
questionOrder always equals y, so it keeps the order of the source document.
"""

import re
import unicodedata
import uuid
from collections.abc import Iterable, Sequence

from forms2json.domain.form_definition import Question

GRID_COLS = 3
FALLBACK_TECH_NAME = "pole"


def new_id() -> str:
    return str(uuid.uuid4())


def layout_page(sections: Sequence[Question]) -> None:
    """Places sections (and their fields) one under another, in the given order."""
    y = 0
    for section in sections:
        _place(section, y, rows=len(section.field.repeating_section_grid) + 1)
        for index, child in enumerate(section.field.repeating_section_grid):
            _place(child, index, rows=1)
        y += section.rows


def _place(question: Question, y: int, rows: int) -> None:
    question.x, question.y, question.rows, question.cols = 0, y, rows, GRID_COLS
    question.field.question_order = y


def slugify(label: str) -> str:
    """'Adres e-mail' -> 'adres_e_mail': lowercase ASCII words joined with '_'."""
    # NFKD splits ą, ę, ó... into letter + accent; ł has no decomposition, so map it first.
    text = unicodedata.normalize("NFKD", label.lower().replace("ł", "l"))
    ascii_text = text.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")


class TechNames:
    """Hands out techNames unique within a form; repeats get _2, _3... as in the references."""

    def __init__(self, taken: Iterable[str] = ()) -> None:
        self._taken = set(taken)

    def new(self, label: str) -> str:
        base = slugify(label) or FALLBACK_TECH_NAME
        name, n = base, 1
        while name in self._taken:
            n += 1
            name = f"{base}_{n}"
        self._taken.add(name)
        return name
