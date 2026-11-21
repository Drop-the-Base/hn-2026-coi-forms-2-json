from abc import ABC, abstractmethod

from forms2json.domain.document import NormalizedDocument


class ExtractionFailed(ValueError):
    """The file is damaged, crafted or too large to read; the message never quotes its content."""


class DocumentReader(ABC):
    """Turns raw file bytes into a format-independent document."""

    @abstractmethod
    def supports(self, mime_type: str) -> bool: ...

    @abstractmethod
    def read(self, content: bytes) -> NormalizedDocument:
        """Raises ExtractionFailed instead of the parser's own errors."""
