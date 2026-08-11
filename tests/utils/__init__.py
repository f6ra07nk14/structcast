"""Tests for StructCast utilities."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from structcast.utils.base import configure_security, register_dir, unregister_dir


@contextmanager
def configure_security_context(
    dangerous_dunders: Optional[set[str]] = None,
    ascii_check: Optional[bool] = None,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
) -> Generator[None, None, None]:
    """Context manager to temporarily configure security settings."""
    try:
        configure_security(
            dangerous_dunders=dangerous_dunders,
            ascii_check=ascii_check,
            protected_member_check=protected_member_check,
            private_member_check=private_member_check,
        )
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
