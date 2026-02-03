"""Tests for StructCast utilities."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from structcast.utils.security import configure_security, register_dir, unregister_dir


@contextmanager
def configure_security_context(
    blocked_modules: Optional[set[str]] = None,
    allowed_modules: Optional[dict[str, Optional[set[Optional[str]]]]] = None,
) -> Generator[None, None, None]:
    """Context manager to temporarily configure security settings."""
    try:
        configure_security(allowed_modules=allowed_modules, blocked_modules=blocked_modules)
        yield
    finally:
        configure_security()


@contextmanager
def temporary_registered_dir(path: Path) -> Generator[None, None, None]:
    """Context manager to temporarily register a directory for imports."""
    try:
        register_dir(path)
        yield
    finally:
        unregister_dir(path)
