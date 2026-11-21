import asyncio
import logging

from forms2json.application.ports.pdf_renderer import PdfRenderer
from forms2json.domain.upload import (
    DOC,
    DOCX,
    ODS,
    XLSX,
    InvalidUpload,
    UnsupportedFileType,
    validate_upload,
)

# PDF and JPG/PNG the browser shows by itself, so only these go through the renderer.
OFFICE_TYPES = frozenset({DOC, DOCX, XLSX, ODS})

logger = logging.getLogger(__name__)


class RenderPreview:
    """The uploaded office file as PDF for the review screen's "Oryginał" (FR-E4).

    Stateless: nothing is stored, the temp files of the conversion are gone on return (NFR-06).
    """

    def __init__(self, renderer: PdfRenderer, max_upload_bytes: int) -> None:
        self._renderer = renderer
        self._max_upload_bytes = max_upload_bytes

    async def execute(self, filename: str, content: bytes) -> bytes:
        try:
            mime_type = validate_upload(filename, content, self._max_upload_bytes)
            if mime_type not in OFFICE_TYPES:
                raise UnsupportedFileType(
                    "Podgląd PDF jest tylko dla plików DOC, DOCX, XLSX i ODS."
                )
        except InvalidUpload as error:
            logger.info("Preview rejected: %s", type(error).__name__)  # never the file name
            raise
        # soffice blocks for seconds; a thread keeps the event loop serving other requests.
        return await asyncio.to_thread(self._renderer.render, content, mime_type)
