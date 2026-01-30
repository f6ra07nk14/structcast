"""Base utility functions for StructCast."""

import importlib
import logging
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from structcast.utils.constants import DEFAULT_ALLOWED_MODULES, DEFAULT_BLOCKED_BUILTINS, DEFAULT_BLOCKED_MODULES

__logger = logging.getLogger(__name__)

# Registered directories for module searching
__directories: list[Path] = []

# Global security settings
__blocked_modules: set[str] = DEFAULT_BLOCKED_MODULES.copy()
__blocked_builtins: set[str] = DEFAULT_BLOCKED_BUILTINS.copy()
__allowed_modules: set[Optional[str]] = DEFAULT_ALLOWED_MODULES.copy()


class SecurityError(Exception):
    """Exception raised when a security check fails."""


def configure_security(
    blocked_modules: Optional[set[str]] = None,
    blocked_builtins: Optional[set[str]] = None,
    allowed_modules: Optional[set[Optional[str]]] = None,
) -> None:
    """Configure security settings for import_from_address.

    Args:
        blocked_modules (Optional[set[str]]): Set of module names to block. If None, uses default blocked modules.
        blocked_builtins (Optional[set[str]]): Set of builtin names to block. If None, uses default blocked builtins.
        allowed_modules (Optional[set[Optional[str]]]): If provided, only these modules are allowed (allowlist mode).
            If None, uses default allowed modules. If set contains None, all modules are allowed.
    """
    __blocked_modules.clear()
    __blocked_modules.update(blocked_modules or DEFAULT_BLOCKED_MODULES)
    __blocked_builtins.clear()
    __blocked_builtins.update(blocked_builtins or DEFAULT_BLOCKED_BUILTINS)
    __allowed_modules.clear()
    __allowed_modules.update(allowed_modules or DEFAULT_ALLOWED_MODULES)


def get_security_settings() -> dict[str, Any]:
    """Get the current security settings.

    Returns:
        dict[str, Any]: A dictionary containing the current security settings.
    """
    return {
        "blocked_modules": __blocked_modules.copy(),
        "blocked_builtins": __blocked_builtins.copy(),
        "allowed_modules": __allowed_modules.copy(),
    }


def register_dir(path: PathLike) -> None:
    """Register a directory to search for modules.

    Args:
        path (PathLike): The path to the directory to register.
    """
    if not isinstance(path, Path):
        path = Path(path)
    path = path.resolve(strict=True)
    if path in __directories:
        __logger.warning(f"Directory is already registered. Skip registering: {path}")
    else:
        __directories.append(path)


def check_path(path: PathLike) -> Path:
    """Check if a path exists, searching in registered directories if necessary.

    Args:
        path (PathLike): The path to check.

    Returns:
        Path: The resolved path.
    """
    if not isinstance(path, Path):
        path = Path(path)
    if path.exists():
        return path
    if not path.is_absolute():
        for directory in __directories:
            candidate = directory / path
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"Path does not exist: {path}")


def load_module(module_name: str, module_file: PathLike) -> ModuleType:
    """Load a module from a file.

    Args:
        module_name (str): The name of the module.
        module_file (PathLike): The path to the module file.

    Returns:
        ModuleType: The loaded module.
    """
    module_spec = importlib.util.spec_from_file_location(module_name, module_file)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {module_file}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _validate_import(module_name: str, target: str) -> None:
    """Validate that an import is safe.

    Args:
        module_name (str): The module name to import from.
        target (str): The target name to import.

    Raises:
        SecurityError: If the import is blocked by security settings.
    """
    names = module_name.split(".")
    if None not in __allowed_modules and names[0] not in __allowed_modules:
        raise SecurityError(f'Module "{module_name}.{target}" is not in the allowlist.')
    if any(n in __blocked_modules for n in names):
        raise SecurityError(f'Module "{module_name}.{target}" is blocked.')
    if module_name == "builtins" and target in __blocked_builtins:
        raise SecurityError(f'Builtin "{target}" is blocked.')


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
    security_check: bool = True,
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
        if module_name is None:
            module_name = check_path(module_file).stem
        module = load_module(module_name, module_file)
    elif module_name is not None:
        module = importlib.import_module(module_name)
    elif default_module is None:
        module, module_name = importlib.import_module("builtins"), "builtins"
    else:
        module, module_name = default_module, default_module.__name__
    if security_check:
        _validate_import(module_name, target)
    if hasattr(module, target):
        return getattr(module, target)
    raise ImportError(f'Target "{target}" not found in module "{module_name}".')
