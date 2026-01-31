"""Base utility functions for StructCast."""

import importlib
import importlib.util
import logging
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any, Optional, cast

from structcast.utils.constants import (
    DEFAULT_ALLOWED_BUILTINS,
    DEFAULT_ALLOWED_MODULES,
    DEFAULT_BLOCKED_MODULES,
    DEFAULT_DANGEROUS_DUNDERS,
)

__logger = logging.getLogger(__name__)

# Registered directories for module searching
__allowed_directories: list[Path] = []

# Global security settings
__blocked_modules: set[str] = DEFAULT_BLOCKED_MODULES.copy()
__allowed_builtins: set[str] = DEFAULT_ALLOWED_BUILTINS.copy()
__allowed_modules: set[Optional[str]] = cast(set[Optional[str]], DEFAULT_ALLOWED_MODULES.copy())
__dangerous_dunders: set[str] = DEFAULT_DANGEROUS_DUNDERS.copy()


class SecurityError(Exception):
    """Exception raised when a security check fails."""


def configure_security(
    blocked_modules: Optional[set[str]] = None,
    allowed_builtins: Optional[set[str]] = None,
    allowed_modules: Optional[set[Optional[str]]] = None,
    dangerous_dunders: Optional[set[str]] = None,
) -> None:
    """Configure security settings for import_from_address.

    Args:
        blocked_modules (Optional[set[str]]): Set of module names to block. If None, uses default blocked modules.
        allowed_builtins (Optional[set[str]]): Set of builtin names to allow. If None, uses default allowed builtins.
        allowed_modules (Optional[set[Optional[str]]]): If provided, only these modules are allowed (allowlist mode).
            If None, uses default allowed modules. If set contains None, all modules are allowed.
        dangerous_dunders (Optional[set[str]]): Set of dangerous dunder method names to block. If None, uses default.
    """
    __blocked_modules.clear()
    __blocked_modules.update(DEFAULT_BLOCKED_MODULES if blocked_modules is None else blocked_modules)
    __allowed_builtins.clear()
    __allowed_builtins.update(DEFAULT_ALLOWED_BUILTINS if allowed_builtins is None else allowed_builtins)
    __allowed_modules.clear()
    __allowed_modules.update(DEFAULT_ALLOWED_MODULES if allowed_modules is None else allowed_modules)
    __dangerous_dunders.clear()
    __dangerous_dunders.update(DEFAULT_DANGEROUS_DUNDERS if dangerous_dunders is None else dangerous_dunders)


def _resolve_path(path: Path) -> Optional[Path]:
    # Resolve to absolute path to prevent directory traversal
    try:
        resolved_path = path.resolve(strict=True)
        if resolved_path.exists():
            return resolved_path
    except (OSError, RuntimeError) as e:
        __logger.warning(f"Failed to resolve path {path}: {e}")
    return None


def register_dir(path: PathLike) -> None:
    """Register a directory to search for modules.

    Args:
        path (PathLike): The path to the directory to register.
    """
    if not isinstance(path, Path):
        path = Path(path)
    resolved_path = _resolve_path(path)
    if resolved_path is None or not resolved_path.is_dir():
        raise ValueError(f"Path is not a valid directory: {path}")
    if resolved_path in __allowed_directories:
        __logger.warning(f"Directory is already registered. Skip registering: {path}")
    else:
        __allowed_directories.append(resolved_path)


def unregister_dir(path: PathLike) -> None:
    """Unregister a previously registered directory.

    Args:
        path (PathLike): The path to the directory to unregister.
    """
    if not isinstance(path, Path):
        path = Path(path)
    resolved_path = _resolve_path(path)
    if resolved_path is None or not resolved_path.is_dir():
        raise ValueError(f"Path is not a valid directory: {path}")
    try:
        __allowed_directories.remove(resolved_path)
    except ValueError:
        __logger.warning(f"Directory was not registered. Skip unregistering: {path}")


def check_path(path: PathLike, *, hidden_check: bool = True, working_dir_check: bool = True) -> Path:
    """Check if a path exists, searching in registered directories if necessary.

    Args:
        path (PathLike): The path to check.
        hidden_check (bool): If True, blocks paths with hidden directories (starting with '.'). Default is True.
        working_dir_check (bool): If True, ensures that relative paths resolve within allowed directories.
            Default is True.

    Returns:
        Path: The resolved path.

    Raises:
        FileNotFoundError: If the path does not exist.
        SecurityError: If the path is blocked by security settings.
    """
    if not isinstance(path, Path):
        path = Path(path)
    candidate: Optional[Path] = _resolve_path(path)
    if not path.is_absolute():
        allowed_directories = __allowed_directories.copy()
        while candidate is None and allowed_directories:
            candidate = _resolve_path(allowed_directories.pop(0) / path)
    if candidate is None:
        raise FileNotFoundError(f"Path does not exist: {path}")
    if working_dir_check and not (
        (candidate.is_relative_to(Path.home()) and candidate.is_relative_to(Path.cwd()))
        or any(candidate.is_relative_to(d) for d in __allowed_directories)
    ):
        raise SecurityError(f"Path is outside of allowed directories: {path}")
    if hidden_check and any(p.startswith(".") for p in candidate.parts):
        raise SecurityError(f"Path contains hidden directories which are not allowed: {path}")
    return candidate


def _load_module(module_name: str, module_file: Path) -> ModuleType:
    """Load a module from a file.

    Args:
        module_name (str): The name of the module.
        module_file (Path): The path to the module file.

    Returns:
        ModuleType: The loaded module.

    Raises:
        ImportError: If the module cannot be loaded.
        SecurityError: If the module file is not a .py file.
    """
    # Only allow .py files
    if module_file.suffix != ".py":
        raise SecurityError(f"Module file must be a .py file, got: {module_file.suffix}")
    module_spec = importlib.util.spec_from_file_location(module_name, module_file)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {module_file}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def validate_import(module_name: str, target: str) -> None:
    """Validate that an import is safe.

    Args:
        module_name (str): The module name to import from.
        target (str): The target name to import.

    Raises:
        SecurityError: If the import is blocked by security settings.
    """
    if module_name == "builtins":
        if target not in __allowed_builtins:
            raise SecurityError(f'Builtin "{target}" is blocked.')
    elif None not in __allowed_modules:
        if not any(n and (module_name == n or module_name.startswith(f"{n}.")) for n in __allowed_modules):
            raise SecurityError(f'Module "{module_name}.{target}" is not in the allowlist.')
    if any(n and (module_name == n or module_name.startswith(f"{n}.")) for n in __blocked_modules):
        raise SecurityError(f'Module "{module_name}.{target}" is blocked.')


def validate_attribute(
    target: str,
    *,
    protected_member_check: bool = True,
    private_member_check: bool = True,
    ascii_check: bool = True,
) -> None:
    """Validate that an attribute access is safe.

    Args:
        target (str): The attribute name to access.
        protected_member_check (bool): If True, blocks access to protected members (starting with '_'). Default is True.
        private_member_check (bool): If True, blocks access to private members (starting with '__'). Default is True.
        ascii_check (bool): If True, blocks non-ascii attribute names. Default is True.

    Raises:
        SecurityError: If the attribute access is blocked by security settings.
    """
    if not target.isidentifier() or target != target.strip():
        raise SecurityError(f"Invalid attribute name: {repr(target)}")
    if ascii_check and not target.isascii():
        raise SecurityError(f"Attribute name contains non-ascii characters: {repr(target)}")
    if target in __dangerous_dunders:
        raise SecurityError(f"Attribute name is blocked due to dangerous dunder: {repr(target)}")
    if private_member_check and target.startswith("__"):
        raise SecurityError(f'Target "{target}" is private member and cannot be accessed.')
    elif protected_member_check and target.startswith("_"):
        raise SecurityError(f'Target "{target}" is protected member and cannot be accessed.')


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
    security_check: bool = True,
    hidden_check: bool = True,
    working_dir_check: bool = True,
    protected_member_check: bool = True,
    private_member_check: bool = True,
    ascii_check: bool = True,
) -> Any:
    """Import target from address.

    This function imports a class or function from a module specified by the `address` string.
    The `address` can be in the form of "module.class" or just "class". If the module is not specified,
    it defaults to the `default_module` provided. If `module_file` is provided,
    the module will be loaded from the specified file.

    Security: By default, this function blocks importing from dangerous modules (os, subprocess, etc.)
    and dangerous builtins (eval, exec, etc.) to prevent injection attacks. Use configure_security()
    to customize the security settings.

    Args:
        address (str): The address of the class or function to import, in the form of "module.class" or "class".
        default_module (Optional[ModuleType]): The default module to use if the module is not specified in the address.
            Default is None, which means the built-in module will be used.
        module_file (Optional[PathLike]): Optional path to a module file to load the module from.
        security_check (bool): If True, performs security checks. Use with extreme caution. Default is True.
        hidden_check (bool): If True, blocks paths with hidden directories (starting with '.'). Default is True.
        working_dir_check (bool): If True, ensures that relative paths resolve within allowed directories.
            Default is True.
        protected_member_check (bool): If True, blocks access to protected members (starting with '_'). Default is True.
        private_member_check (bool): If True, blocks access to private members (starting with '__'). Default is True.
        ascii_check (bool): If True, blocks non-ascii attribute names. Default is True.

    Returns:
        Any: The imported target.

    Raises:
        SecurityError: If the import is blocked by security settings.
        ImportError: If the target cannot be imported.
    """
    if "." in address:
        index = address.rindex(".")
        module_name, target = address[:index], address[index + 1 :]
    else:
        module_name, target = None, address
    if module_file is not None:
        module_file = check_path(
            module_file,
            hidden_check=security_check and hidden_check,
            working_dir_check=security_check and working_dir_check,
        )
        module_name = module_name or module_file.stem
        module = _load_module(module_name, module_file)
    elif module_name is not None:
        module = importlib.import_module(module_name)
    elif default_module is None:
        module, module_name = importlib.import_module("builtins"), "builtins"
    else:
        module, module_name = default_module, default_module.__name__
    if security_check:
        validate_import(module_name, target)
        validate_attribute(
            target,
            protected_member_check=protected_member_check,
            private_member_check=private_member_check,
            ascii_check=ascii_check,
        )
    if hasattr(module, target):
        return getattr(module, target)
    raise ImportError(f'Target "{target}" not found in module "{module_name}".')
