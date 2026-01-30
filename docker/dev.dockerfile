# Use Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies using uv sync (recommended method)
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --dev

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set Python path
ENV PYTHONPATH=/app/src

