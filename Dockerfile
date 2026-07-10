# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Doc Helper AI Agent — production image (multi-stage, uv-based)
#
# Build:  docker build -t doc-helper-ai-agent .
# Run:    docker run --rm -p 8000:8000 doc-helper-ai-agent
# The app runs fully offline in deterministic mock mode (no API key required).
# ---------------------------------------------------------------------------

# ---- Stage 1: build the virtual environment with uv -----------------------
# The uv image is based on the official python:3.12-slim-bookworm, so the
# interpreter path matches the runtime stage and the copied venv stays valid.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install only third-party dependencies first (heavily cached layer).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the project source and install the project itself into the venv.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- Stage 2: minimal runtime -------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="doc-helper-ai-agent" \
      org.opencontainers.image.description="Local-first AI agent backend (FastAPI + LangGraph)." \
      org.opencontainers.image.source="https://github.com/etonealbert/doc-helper-ai-agent" \
      org.opencontainers.image.licenses="MIT"

# Run as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

# Copy the fully-populated /app (venv + source + data) from the builder.
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    ENABLE_MOCK_LLM=true

USER app
EXPOSE 8000

# Liveness probe against the health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"]

CMD ["uvicorn", "doc_helper_ai_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
