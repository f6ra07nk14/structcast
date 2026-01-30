"""Base utility functions for StructCast."""

import importlib
import logging
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

logger = logging.getLogger(__name__)

__directories: list[Path] = []


def register_dir(path: PathLike) -> None:
    """Register a directory to search for modules.

    Args:
        path (PathLike): The path to the directory to register.
    """
    if not isinstance(path, Path):
        path = Path(path)
    path = path.resolve(strict=True)
    if path in __directories:
        logger.warning(f"Directory is already registered. Skip registering: {path}")
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


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
) -> Any:
    """Import target from address.

    This function imports a class or function from a module specified by the `address` string.
    The `address` can be in the form of "module.class" or just "class". If the module is not specified,
    it defaults to the `default_module` provided. If `module_file` is provided,
    the module will be loaded from the specified file.

    Args:
        address (str): The address of the class or function to import, in the form of "module.class" or "class".
        default_module (Optional[ModuleType]): The default module to use if the module is not specified in the address.
            Default is None, which means the built-in module will be used.
        module_file (Optional[PathLike]): Optional path to a module file to load the module from.

    Returns:
        Any: The imported target.
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
        module = importlib.import_module("builtins")
    else:
        module = default_module
    if hasattr(module, target):
        return getattr(module, target)
    raise ImportError(f'Target "{target}" not found in module "{module.__name__}".')
