"""Tests for StructCast utilities."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Optional

from structcast.utils.base import configure_security


@contextmanager
def configure_security_context(
    blocked_modules: Optional[set[str]] = None,
    allowed_builtins: Optional[set[str]] = None,
    allowed_modules: Optional[set[Optional[str]]] = None,
) -> Generator[None, None, None]:
    """Context manager to temporarily configure security settings."""
    try:
        configure_security(
            allowed_modules=allowed_modules,
            blocked_modules=blocked_modules,
            allowed_builtins=allowed_builtins,
        )
        yield
    finally:
        configure_security()
