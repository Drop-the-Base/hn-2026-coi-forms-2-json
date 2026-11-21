"""OCR on Tesseract through pytesseract (ADR-0029)."""

import io
from itertools import groupby

import pytesseract  # type: ignore[import-untyped]
from PIL import Image, ImageOps, UnidentifiedImageError

from forms2json.application.ports.document_reader import ExtractionFailed
from forms2json.application.ports.ocr_engine import MAX_PIXELS, OcrEngine
from forms2json.domain.document import TextBlock

# A 200 dpi A4 page takes a few seconds; a stuck tesseract must not hold the worker.
TIMEOUT_SECONDS = 120


class TesseractOcr(OcrEngine):
    def __init__(self, lang: str) -> None:
        self._lang = lang

    def recognize(self, image: bytes) -> tuple[TextBlock, ...]:
        try:
            with Image.open(io.BytesIO(image)) as img:
                if img.width * img.height > MAX_PIXELS:
                    raise ExtractionFailed(f"Obraz jest za duży (maks. {MAX_PIXELS} pikseli).")
                # Phone photos store rotation in EXIF instead of rotating the pixels.
                page = ImageOps.exif_transpose(img)
                data = pytesseract.image_to_data(
                    page,
                    lang=self._lang,
                    output_type=pytesseract.Output.DICT,
                    timeout=TIMEOUT_SECONDS,
                )
        except pytesseract.TesseractNotFoundError:
            raise  # a deployment fault, not a broken file, yet an OSError like the ones below
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
            raise ExtractionFailed(
                "Obraz jest uszkodzony albo ma nieobsługiwany format."
            ) from error
        except pytesseract.TesseractError as error:
            raise ExtractionFailed("OCR nie odczytał obrazu.") from error
        except RuntimeError as error:  # pytesseract signals its timeout this way
            raise ExtractionFailed("OCR trwał za długo.") from error
        return lines(data)


def lines(data: dict[str, list[int | str]]) -> tuple[TextBlock, ...]:
    """Groups Tesseract's word rows (already in reading order) into lines with mean confidence."""
    words = [
        ((block, paragraph, line), str(text).strip(), int(conf))
        for block, paragraph, line, conf, text in zip(
            data["block_num"],
            data["par_num"],
            data["line_num"],
            data["conf"],
            data["text"],
            strict=True,
        )
        # conf -1 marks page, block and line rows, which carry no word.
        if str(text).strip() and int(conf) >= 0
    ]
    result = []
    for _, group in groupby(words, key=lambda word: word[0]):
        line_words = list(group)
        text = " ".join(word for _, word, _ in line_words)
        confidence = sum(conf for *_, conf in line_words) / len(line_words) / 100
        result.append(TextBlock(text, confidence))
    return tuple(result)
