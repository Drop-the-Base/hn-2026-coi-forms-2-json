import io

import pytest
from PIL import Image

from forms2json.adapters.outbound.ocr import tesseract_ocr
from forms2json.adapters.outbound.ocr.tesseract_ocr import TesseractOcr, lines
from forms2json.adapters.outbound.readers.image_reader import ImageReader
from forms2json.application.ports.document_reader import ExtractionFailed
from forms2json.application.ports.ocr_engine import OcrEngine
from forms2json.domain.document import NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.upload import JPEG, PDF, PNG


class FakeOcr(OcrEngine):
    """Returns the given lines for every image and remembers the images it got."""

    def __init__(self, *blocks: TextBlock) -> None:
        self._blocks = blocks
        self.images: list[bytes] = []

    def recognize(self, image: bytes) -> tuple[TextBlock, ...]:
        self.images.append(image)
        return self._blocks


def test_image_is_one_page_of_ocr_lines() -> None:
    reader = ImageReader(FakeOcr(TextBlock("Wniosek", 0.9)))

    assert reader.supports(JPEG) and reader.supports(PNG) and not reader.supports(PDF)
    assert reader.read(b"img").pages == (Page(1, (TextBlock("Wniosek", 0.9),)),)


def test_tesseract_words_are_grouped_into_lines_with_mean_confidence() -> None:
    # Shape of pytesseract.image_to_data(output_type=DICT): page/block/line rows have conf -1.
    data: dict[str, list[int | str]] = {
        "block_num": [1, 1, 1, 1, 1, 2],
        "par_num": [1, 1, 1, 1, 1, 1],
        "line_num": [1, 1, 1, 2, 2, 1],
        "conf": [-1, 90, 70, 80, 50, 60],
        "text": ["", "Imię", "nazwisko", "PESEL", " ", "Data"],
    }

    assert lines(data) == (
        TextBlock("Imię nazwisko", 0.8),
        TextBlock("PESEL", 0.8),
        TextBlock("Data", 0.6),
    )


def test_damaged_image_fails_without_calling_tesseract() -> None:
    with pytest.raises(ExtractionFailed, match="uszkodzony"):
        TesseractOcr("pol").recognize(b"\xff\xd8\xff\xe0 not a jpeg")


def test_image_over_pixel_limit_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tesseract_ocr, "MAX_PIXELS", 99)
    png = io.BytesIO()
    Image.new("L", (10, 10)).save(png, format="PNG")

    with pytest.raises(ExtractionFailed, match="za duży"):
        TesseractOcr("pol").recognize(png.getvalue())


def test_ocr_confidence_is_mean_of_ocr_lines_only() -> None:
    def document(*blocks: TextBlock | Table) -> NormalizedDocument:
        return NormalizedDocument((Page(1, blocks),))

    assert document(TextBlock("a"), Table(())).ocr_confidence is None
    assert document(TextBlock("a", 0.9), TextBlock("b", 0.5)).ocr_confidence == pytest.approx(0.7)
