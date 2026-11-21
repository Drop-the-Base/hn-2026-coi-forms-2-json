from abc import ABC, abstractmethod


class PreviewFailed(ValueError):
    """The document could not be rendered; the message is shown to the user (Polish)."""


class PdfRenderer(ABC):
    """Renders an office document (DOC, DOCX, XLSX, ODS) as PDF to preview the original (FR-E4)."""

    @abstractmethod
    def render(self, content: bytes, mime_type: str) -> bytes:
        """PDF bytes; raises PreviewFailed instead of the converter's own errors."""
