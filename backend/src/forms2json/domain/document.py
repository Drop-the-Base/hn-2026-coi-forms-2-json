from dataclasses import dataclass


@dataclass(frozen=True)
class TextBlock:
    text: str


@dataclass(frozen=True)
class Table:
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Checkbox:
    label: str
    checked: bool


type Block = TextBlock | Table | Checkbox


@dataclass(frozen=True)
class Page:
    number: int
    # Blocks keep reading order, so the LLM sees fields next to their labels.
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class NormalizedDocument:
    """Format-independent output of the Ingest step."""

    pages: tuple[Page, ...]
