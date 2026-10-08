# Multi-stage build leveraging Astral uv for fast, reliable dependency installation
FROM ghcr.io/astral-sh/uv:0.5.21 AS uv_binary
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install uv from official binary image
COPY --from=uv_binary /uv /uvx /bin/

# Install dependencies first for optimal Docker layer caching
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

# Copy application source and configuration
COPY src/ ./src/
COPY eval/ ./eval/
COPY data/ ./data/
COPY frontend/ ./frontend/
COPY Makefile meta.yaml ./

# Complete uv sync
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
