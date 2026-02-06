ARG PY_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PY_VERSION}-bookworm-slim

# Define Python versions variable
ARG PYTHON_VERSIONS="3.8 3.9 3.10 3.11 3.12 3.13 3.14"

# Set working directory
WORKDIR /app

# Install multiple Python versions
RUN uv python install $PYTHON_VERSIONS --preview

# Install dependencies using uv sync (recommended method)
# The venv created in /app/.venv will be reused in CI via PATH
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --dev --group tox

# Activate virtual environment and set up PATH to use installed tools
ENV PATH="/app/.venv/bin:${PATH}"

# Set Python path
ENV PYTHONPATH=/app/src

