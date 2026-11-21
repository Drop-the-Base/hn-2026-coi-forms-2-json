"""Real Tesseract with the Polish pack; runs in the worker image or where tesseract is installed."""

from pathlib import Path

import pytest

from forms2json.adapters.outbound.ocr.tesseract_ocr import TesseractOcr

DATA = Path(__file__).parents[3] / "data"

pytestmark = pytest.mark.integration


def test_form_3_scan_reads_polish_title_with_confidence() -> None:
    (jpg,) = DATA.glob("3. */*.jpg")

    blocks = TesseractOcr("pol").recognize(jpg.read_bytes())

    text = " ".join(block.text for block in blocks)
    assert "zaświadczenia" in text.lower()
    assert all(block.confidence is not None and 0 <= block.confidence <= 1 for block in blocks)
