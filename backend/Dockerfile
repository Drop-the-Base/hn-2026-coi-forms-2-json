# syntax=docker/dockerfile:1
# Two images from one file: `docker build --target api .` and `--target worker .` (NFR-07).
# Base images pinned by tag and multi-arch digest (ADR-0012); bump tag and digest together.

FROM ghcr.io/astral-sh/uv:0.11.14@sha256:1025398289b62de8269e70c45b91ffa37c373f38118d7da036fb8bb8efc85d97 AS uv

# api runs on Alpine: every dependency ships a musllinux wheel (ADR-0012).
FROM python:3.14.10-alpine3.24@sha256:5862d971d1f0ae26b258cefa4e893556b1d3aba81bd2ff30888704ad378bab67 AS api-build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

# The venv links to the base image's interpreter, so it is built on the same base it runs on.
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS worker-build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

FROM python:3.14.10-alpine3.24@sha256:5862d971d1f0ae26b258cefa4e893556b1d3aba81bd2ff30888704ad378bab67 AS api
RUN adduser -D -u 10001 app
COPY --from=api-build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO /dev/null http://127.0.0.1:8000/health || exit 1
CMD ["uvicorn", "forms2json.bootstrap:create_api", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Worker on Debian slim: LibreOffice converts .doc to .docx (ADR-0012, ADR-0013).
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS worker
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-writer-nogui \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=worker-build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH
# soffice writes its profile under $HOME, hence a real home directory.
USER 10001
CMD ["python", "-m", "forms2json.adapters.inbound.worker"]
