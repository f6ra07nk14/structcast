"""Security-related utilities and settings for structcast."""

from dataclasses import field
import logging
from pathlib import Path
from typing import Optional

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

    allowed_directories: list[Path] = field(default_factory=list)
    blocked_modules: set[str] = field(default_factory=lambda: DEFAULT_BLOCKED_MODULES.copy())
    allowed_builtins: set[str] = field(default_factory=lambda: DEFAULT_ALLOWED_BUILTINS.copy())
    allowed_modules: set[Optional[str]] = field(default_factory=lambda: DEFAULT_ALLOWED_MODULES.copy())
    dangerous_dunders: set[str] = field(default_factory=lambda: DEFAULT_DANGEROUS_DUNDERS.copy())
    ascii_check: bool = True
    protected_member_check: bool = True
    private_member_check: bool = True
    hidden_check: bool = True
    working_dir_check: bool = True


__settings = SecuritySettings()
"""Global security settings instance."""


def configure_security(
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
    __settings.blocked_modules.clear()
    __settings.blocked_modules.update(DEFAULT_BLOCKED_MODULES if blocked_modules is None else blocked_modules)
    __settings.allowed_builtins.clear()
    __settings.allowed_builtins.update(DEFAULT_ALLOWED_BUILTINS if allowed_builtins is None else allowed_builtins)
    __settings.allowed_modules.clear()
    __settings.allowed_modules.update(DEFAULT_ALLOWED_MODULES if allowed_modules is None else allowed_modules)
    __settings.dangerous_dunders.clear()
    __settings.dangerous_dunders.update(DEFAULT_DANGEROUS_DUNDERS if dangerous_dunders is None else dangerous_dunders)


def register_dir(path: PathLike) -> None:
    """Register a directory to search for modules.

    Args:
        path (PathLike): The path to the directory to register.
    """
    if not isinstance(path, Path):
        path = Path(path)
    resolved_path = resolve_path(path)
    if resolved_path is None or not resolved_path.is_dir():
        raise ValueError(f"Path is not a valid directory: {path}")
    if resolved_path in __settings.allowed_directories:
        logger.warning(f"Directory is already registered. Skip registering: {path}")
    else:
        __settings.allowed_directories.append(resolved_path)


def unregister_dir(path: PathLike) -> None:
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
        __settings.allowed_directories.remove(resolved_path)
    except ValueError:
        logger.warning(f"Directory was not registered. Skip unregistering: {path}")


def validate_import(module_name: str, target: str) -> None:
    """Validate that an import is safe.

    Args:
        module_name (str): The module name to import from.
        target (str): The target name to import.

    Raises:
        SecurityError: If the import is blocked by security settings.
    """
    if module_name == "builtins":
        if target not in __settings.allowed_builtins:
            raise SecurityError(f"Blocked builtin import attempt: {target}")
    elif None not in __settings.allowed_modules:
        if not any(n and (module_name == n or module_name.startswith(f"{n}.")) for n in __settings.allowed_modules):
            raise SecurityError(f"Blocked import attempt (not in allowlist): {module_name}.{target}")
    if any(n and (module_name == n or module_name.startswith(f"{n}.")) for n in __settings.blocked_modules):
        raise SecurityError(f"Blocked import attempt (blocklisted): {module_name}.{target}")


def _validate_attribute(
    target: str,
    *,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> None:
    ascii_check = __settings.ascii_check if ascii_check is None else ascii_check
    protected_member_check = (
        __settings.protected_member_check if protected_member_check is None else protected_member_check
    )
    private_member_check = __settings.private_member_check if private_member_check is None else private_member_check
    if not target.isidentifier() or target != target.strip():
        raise SecurityError(f"Invalid attribute access attempt: {repr(target)}")
    if ascii_check and not target.isascii():
        raise SecurityError(f"Non-ASCII attribute access attempt: {repr(target)}")
    if target in __settings.dangerous_dunders:
        raise SecurityError(f"Dangerous dunder access attempt: {repr(target)}")
    is_private = target.startswith("__")
    is_protected = target.startswith("_") and not is_private
    if private_member_check and is_private:
        raise SecurityError(f"Private member access attempt: {repr(target)}")
    elif protected_member_check and is_protected:
        raise SecurityError(f"Protected member access attempt: {repr(target)}")


def validate_attribute(
    target: str,
    *,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> None:
    """Validate that a dotted attribute access is safe.

    Args:
        target (str): The dotted attribute name to access.
        protected_member_check (Optional[bool]): Whether to block access to protected members (starting with '_').
            Default is taken from global settings.
        private_member_check (Optional[bool]): Whether to block access to private members (starting with '__').
            Default is taken from global settings.
        ascii_check (Optional[bool]): Whether to block access to non-ASCII attribute names.
            Default is taken from global settings.

    Raises:
        SecurityError: If the attribute access is blocked by security settings.
    """
    attrs = target.split(".")
    for ind, attr in enumerate(attrs):
        try:
            _validate_attribute(
                attr,
                protected_member_check=protected_member_check,
                private_member_check=private_member_check,
                ascii_check=ascii_check,
            )
        except SecurityError as e:
            raise SecurityError(f'Invalid attribute access attempt at "{".".join(attrs[: ind + 1])}": {e}') from e


def check_path(
    path: PathLike,
    *,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
) -> Path:
    """Check if a path exists, searching in registered directories if necessary.

    Args:
        path (PathLike): The path to check.
        hidden_check (Optional[bool]): Whether to block paths with hidden directories (starting with '.').
            Default is taken from global settings.
        working_dir_check (Optional[bool]): Whether to ensure that relative paths resolve within allowed directories.
            Default is taken from global settings.

    Returns:
        Path: The resolved path.

    Raises:
        FileNotFoundError: If the path does not exist.
        SecurityError: If the path is blocked by security settings.
    """
    hidden_check = __settings.hidden_check if hidden_check is None else hidden_check
    working_dir_check = __settings.working_dir_check if working_dir_check is None else working_dir_check
    if not isinstance(path, Path):
        path = Path(path)
    candidate: Optional[Path] = resolve_path(path)
    if not path.is_absolute():
        allowed_directories = __settings.allowed_directories.copy()
        while candidate is None and allowed_directories:
            candidate = resolve_path(allowed_directories.pop(0) / path)
    if candidate is None:
        raise FileNotFoundError(f"Path does not exist: {path}")
    if working_dir_check and not (
        (candidate.is_relative_to(Path.home()) and candidate.is_relative_to(Path.cwd()))
        or any(candidate.is_relative_to(d) for d in __settings.allowed_directories)
    ):
        raise SecurityError(f"Path is outside of allowed directories: {path}")
    if hidden_check and any(p.startswith(".") for p in candidate.parts):
        raise SecurityError(f"Path contains hidden directories which are not allowed: {path}")
    return candidate
