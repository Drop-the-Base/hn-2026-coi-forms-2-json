from abc import ABC, abstractmethod

from forms2json.domain.document import NormalizedDocument


class DocumentReader(ABC):
    """Turns raw file bytes into a format-independent document."""

    @abstractmethod
    def supports(self, mime_type: str) -> bool: ...

    @abstractmethod
    def read(self, content: bytes) -> NormalizedDocument: ...
