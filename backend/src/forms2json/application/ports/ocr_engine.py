from abc import ABC, abstractmethod

from forms2json.domain.document import TextBlock

# A4 at 600 dpi is ~35 Mpx; anything bigger is a decompression bomb, not a form.
MAX_PIXELS = 50_000_000


class OcrEngine(ABC):
    """Reads text from a page image (JPEG or PNG bytes)."""

    @abstractmethod
    def recognize(self, image: bytes) -> tuple[TextBlock, ...]:
        """Text lines in reading order, each with the mean confidence of its words (0..1).

        Raises ExtractionFailed for an unreadable, too slow or over MAX_PIXELS image.
        """
