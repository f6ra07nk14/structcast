"""Security-related utilities and settings for structcast."""

from dataclasses import field
import logging
from pathlib import Path
from typing import Optional, cast

from structcast.utils.constants import (
    DEFAULT_ALLOWED_BUILTINS,
    DEFAULT_ALLOWED_MODULES,
    DEFAULT_BLOCKED_MODULES,
    DEFAULT_DANGEROUS_DUNDERS,
)
from structcast.utils.dataclasses import dataclass
from structcast.utils.types import PathLike

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Exception raised when a security check fails."""


def resolve_path(path: Path) -> Optional[Path]:
    """Resolve a path safely, returning None if it cannot be resolved.

    Args:
        path (Path): The path to resolve.

    Returns:
        Optional[Path]: The resolved path, or None if it cannot be resolved.
    """
    try:
        resolved_path = path.resolve(strict=True)
        if resolved_path.exists():
            return resolved_path
    except (OSError, RuntimeError) as e:
        logger.warning(f"Failed to resolve path {path}: {e}")
    return None


@dataclass
class SecuritySettings:
    """Settings for security-related restrictions."""

    __allowed_directories: list[Path] = field(default_factory=list)
    __blocked_modules: set[str] = field(default_factory=lambda: DEFAULT_BLOCKED_MODULES.copy())
    __allowed_builtins: set[str] = field(default_factory=lambda: DEFAULT_ALLOWED_BUILTINS.copy())
    __allowed_modules: set[Optional[str]] = field(
        default_factory=lambda: cast(set[Optional[str]], DEFAULT_ALLOWED_MODULES.copy())
    )
    __dangerous_dunders: set[str] = field(default_factory=lambda: DEFAULT_DANGEROUS_DUNDERS.copy())
    ascii_check: bool = True
    protected_member_check: bool = True
    private_member_check: bool = True
    hidden_check: bool = True
    working_dir_check: bool = True

    def configure_security(
        self,
        blocked_modules: Optional[set[str]] = None,
        allowed_builtins: Optional[set[str]] = None,
        allowed_modules: Optional[set[Optional[str]]] = None,
        dangerous_dunders: Optional[set[str]] = None,
    ) -> None:
        """Configure security settings for import_from_address.

        Args:
            blocked_modules (Optional[set[str]]): Set of module names to block. If None, use default blocked modules.
            allowed_builtins (Optional[set[str]]): Set of builtin names to allow. If None, use default allowed builtins.
            allowed_modules (Optional[set[Optional[str]]]): Set of module names to allow.
                If None, use default allowed modules. If set to an empty set, all modules are blocked.
                If set to None, all modules except blocked ones are allowed.
            dangerous_dunders (Optional[set[str]]): Set of dangerous dunder method names to block. If None, use default.
        """
        self.__blocked_modules.clear()
        self.__blocked_modules.update(DEFAULT_BLOCKED_MODULES if blocked_modules is None else blocked_modules)
        self.__allowed_builtins.clear()
        self.__allowed_builtins.update(DEFAULT_ALLOWED_BUILTINS if allowed_builtins is None else allowed_builtins)
        self.__allowed_modules.clear()
        self.__allowed_modules.update(DEFAULT_ALLOWED_MODULES if allowed_modules is None else allowed_modules)
        self.__dangerous_dunders.clear()
        self.__dangerous_dunders.update(DEFAULT_DANGEROUS_DUNDERS if dangerous_dunders is None else dangerous_dunders)

    def register_dir(self, path: PathLike) -> None:
        """Register a directory to search for modules.

        Args:
            path (PathLike): The path to the directory to register.
        """
        if not isinstance(path, Path):
            path = Path(path)
        resolved_path = resolve_path(path)
        if resolved_path is None or not resolved_path.is_dir():
            raise ValueError(f"Path is not a valid directory: {path}")
        if resolved_path in self.__allowed_directories:
            logger.warning(f"Directory is already registered. Skip registering: {path}")
        else:
            self.__allowed_directories.append(resolved_path)

    def unregister_dir(self, path: PathLike) -> None:
        """Unregister a previously registered directory.

        Args:
            path (PathLike): The path to the directory to unregister.
        """
        if not isinstance(path, Path):
            path = Path(path)
        resolved_path = resolve_path(path)
        if resolved_path is None or not resolved_path.is_dir():
            raise ValueError(f"Path is not a valid directory: {path}")
        try:
            self.__allowed_directories.remove(resolved_path)
        except ValueError:
            logger.warning(f"Directory was not registered. Skip unregistering: {path}")

    @property
    def allowed_directories(self) -> tuple[Path, ...]:
        """Get the list of allowed directories."""
        return tuple(self.__allowed_directories)

    @property
    def blocked_modules(self) -> tuple[str, ...]:
        """Get the set of blocked modules."""
        return tuple(self.__blocked_modules)

    @property
    def allowed_builtins(self) -> tuple[str, ...]:
        """Get the set of allowed builtins."""
        return tuple(self.__allowed_builtins)

    @property
    def allowed_modules(self) -> tuple[Optional[str], ...]:
        """Get the set of allowed modules."""
        return tuple(self.__allowed_modules)

    @property
    def dangerous_dunders(self) -> tuple[str, ...]:
        """Get the set of dangerous dunder methods."""
        return tuple(self.__dangerous_dunders)


SECURITY_SETTINGS = SecuritySettings()
"""Global security settings instance."""
