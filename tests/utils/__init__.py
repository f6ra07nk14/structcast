"""Tests for StructCast utilities."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from structcast.utils.security import SECURITY_SETTINGS


@contextmanager
def configure_security_context(
    blocked_modules: Optional[set[str]] = None,
    allowed_builtins: Optional[set[str]] = None,
    allowed_modules: Optional[set[Optional[str]]] = None,
) -> Generator[None, None, None]:
    """Context manager to temporarily configure security settings."""
    try:
        SECURITY_SETTINGS.configure_security(
            allowed_modules=allowed_modules,
            blocked_modules=blocked_modules,
            allowed_builtins=allowed_builtins,
        )
        yield
    finally:
        SECURITY_SETTINGS.configure_security()


@contextmanager
def temporary_registered_dir(path: Path) -> Generator[None, None, None]:
    """Context manager to temporarily register a directory for imports."""
    try:
        SECURITY_SETTINGS.register_dir(path)
        yield
    finally:
        SECURITY_SETTINGS.unregister_dir(path)
