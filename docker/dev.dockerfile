ARG PY_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PY_VERSION}-bookworm-slim

# Define user variable and Python versions variable
ARG CI_USER=ciuser
ARG PYTHON_VERSIONS="3.8 3.9 3.10 3.11 3.12 3.13 3.14"

# Create a non-root user and configure the environment
RUN useradd -m -s /bin/bash $CI_USER

# Switch to non-root user
USER $CI_USER
WORKDIR /home/$CI_USER

# Install multiple Python versions using `uv` as the non-root user
RUN uv python install $PYTHON_VERSIONS --preview --install-dir /home/$CI_USER/.local/bin

# Install dependencies using uv sync (recommended method)
# The venv created in /home/ciuser/.venv will be reused in CI via PATH
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --dev --group tox

# Activate virtual environment and set up PATH to use installed tools
ENV PATH="/home/$CI_USER/.venv/bin:/home/$CI_USER/.local/bin:${PATH}"

# Set Python path
ENV PYTHONPATH=/home/$CI_USER/src

