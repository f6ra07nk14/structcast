# Use Python base image
ARG PY_VERSION=3.9
FROM ghcr.io/astral-sh/uv:python${PY_VERSION}-bookworm-slim

# Set working directory
WORKDIR /app

# Install dependencies using uv sync (recommended method)
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --dev

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set Python path
ENV PYTHONPATH=/app/src

