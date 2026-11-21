# syntax=docker/dockerfile:1
# Two images from one file: `docker build --target api .` and `--target worker .` (NFR-07).
# Base images pinned by tag and multi-arch digest (ADR-0012); bump tag and digest together.

FROM ghcr.io/astral-sh/uv:0.11.14@sha256:1025398289b62de8269e70c45b91ffa37c373f38118d7da036fb8bb8efc85d97 AS uv

# One venv for both images. Both run on Debian slim: the musllinux wheels of pypdfium2
# (pdfplumber) bundle GPL code, the manylinux ones do not (ADR-0012, ADR-0013).
# The venv links to the base image's interpreter, so it is built on the same base it runs on.
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

# Api on Debian slim: LibreOffice renders DOC, DOCX, XLSX and ODS as PDF for the preview of
# the original on the review screen (ADR-0031).
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS api
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-writer-nogui libreoffice-calc-nogui \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH
# soffice writes its profile under $HOME, hence a real home directory.
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "forms2json.bootstrap:create_api", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Worker on Debian slim: LibreOffice converts .doc to .docx, Tesseract reads scans and images
# (ADR-0012, ADR-0013, ADR-0029).
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS worker
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-writer-nogui tesseract-ocr tesseract-ocr-pol \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH
# soffice writes its profile under $HOME, hence a real home directory.
USER 10001
CMD ["python", "-m", "forms2json.adapters.inbound.worker"]
