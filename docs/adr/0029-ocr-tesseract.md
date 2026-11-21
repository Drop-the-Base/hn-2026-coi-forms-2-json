# ADR-0029: OCR obrazów i skanów PDF: Tesseract + pytesseract

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-02, FR-T1, NFR-03, NFR-13, NFR-16

## Kontekst

FR-02 wymaga czytania JPG/PNG i skanów PDF. W `data/` każdy formularz ma wersję JPG i PNG (A4, 200 dpi, 1654×2339 px). OCR musi działać lokalnie, bez GPU i bez zewnętrznych API (NFR-03), na licencji z [ADR-0013](0013-polityka-licencji.md). Do wyniku potrzebna jest pewność rozpoznania (FR-T1, [architecture.md §4](../architecture.md)).

## Decyzja

**Tesseract 5** (Apache-2.0) z pakietem językowym `pol` (dane `tessdata`, Apache-2.0), wołany przez **`pytesseract`** (Apache-2.0; zależności: `packaging` Apache-2.0/BSD-2, `Pillow` MIT-CMU). Pakiety apt `tesseract-ocr` i `tesseract-ocr-pol` są tylko w obrazie `worker`. Zależności biblioteki z Debiana (Leptonica, libtiff, libpng, libjpeg, libwebp, libopenjp2, libarchive) są na licencjach permisywnych.

- Port `OcrEngine` (`application/ports/ocr_engine.py`): bajty obrazu → linie tekstu (`TextBlock`) w kolejności czytania, z `confidence` = średnia pewność słów linii (0..1). Adapter `TesseractOcr` grupuje wiersze `image_to_data` po (blok, akapit, linia).
- `ImageReader`: JPG/PNG = jedna strona z OCR. `PdfReader`: strona z obrazami i bez warstwy tekstowej jest renderowana (pdfplumber → pypdfium2, 300 dpi) i idzie do OCR zamiast błędu.
- Język z `OCR_LANG` (domyślnie `pol`).
- Ochrona: limit 50 Mpx dla obrazu (sprawdzany przed dekodowaniem) i dla renderowanej strony PDF (sprawdzany przed renderowaniem), limit 100 stron PDF z [ADR-0023](0023-odczyt-pdf-pdfplumber.md), timeout 120 s na stronę.
- Pewność: średnia pewność OCR dokumentu ogranicza z góry confidence każdego elementu. Poniżej progu przeglądu (`CONFIDENCE_REVIEW_THRESHOLD`) wynik dostaje ostrzeżenie `OCR-LOW-CONFIDENCE`.

Pomiar (formularz 3, JPG, Tesseract z Homebrew na macOS, dane `pol`): OCR 0,6 s, 94% słów z wersji DOCX odczytanych (precyzja 90%), średnia pewność 0,87.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| EasyOCR, PaddleOCR | PyTorch/Paddle, setki MB i modele do pobrania; bez GPU wolne |
| docTR | j.w. (PyTorch), lepszy układ, ale ciężki obraz |
| OCRmyPDF | dobudowuje warstwę tekstową PDF przez Tesseracta, ale ciągnie Ghostscript (AGPL) |
| tesserocr | wiązanie C-API, szybsze, ale wymaga kompilacji z nagłówkami Tesseracta |
| Chmurowe OCR (Google, Azure) | zewnętrzne API, zakazane (NFR-03) |

## Konsekwencje

- Obraz workera rośnie o Tesseracta z danymi `pol` i `eng`; rozmiar do zmierzenia po buildzie (sieć do Docker Hub padała przy pracy nad #25).
- Tesseract nie rozpoznaje pól wyboru ani tabel: kratki stają się śmieciowymi znakami (np. `m».`), a tabele liniami tekstu. Understand dostaje surowy tekst.
- Cięcia wysokich obrazów na strony A4 ([architecture.md §4](../architecture.md)) nie robimy: wszystkie obrazy w `data/` to pojedyncze strony A4.
- Pewność OCR jest jedna dla dokumentu, nie per pole: nie wiemy, z której linii LLM wziął pole.
