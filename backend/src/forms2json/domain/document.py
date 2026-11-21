from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFile:
    """Input of the Ingest step: the uploaded bytes and the MIME type detected at upload."""

    content: bytes
    mime_type: str


@dataclass(frozen=True)
class TextBlock:
    text: str
    # Mean OCR confidence of the words (0..1); None for text read from a text layer.
    confidence: float | None = None


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

    @property
    def ocr_confidence(self) -> float | None:
        """Mean confidence of the OCR-read lines; None when nothing came from OCR."""
        scores = [
            block.confidence
            for page in self.pages
            for block in page.blocks
            if isinstance(block, TextBlock) and block.confidence is not None
        ]
        return sum(scores) / len(scores) if scores else None
