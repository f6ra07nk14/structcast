"""Base utility functions for StructCast."""

import importlib
import importlib.util
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from ruamel.yaml import YAML

from structcast.utils.security import SecurityError, check_path, validate_attribute, validate_import


def __load_module(module_name: str, module_file: Path) -> ModuleType:
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


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
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
        hidden_check (Optional[bool]): Whether to block paths with hidden directories (starting with '.').
            Default is taken from global settings.
        working_dir_check (Optional[bool]): Whether to ensure that relative paths resolve within allowed directories.
            Default is taken from global settings.
        protected_member_check (Optional[bool]): Whether to block access to protected members (starting with '_').
            Default is taken from global settings.
        private_member_check (Optional[bool]): Whether to block access to private members (starting with '__').
            Default is taken from global settings.
        ascii_check (Optional[bool]): Whether to block access to non-ASCII attribute names.
            Default is taken from global settings.

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
        module_file = check_path(module_file, hidden_check=hidden_check, working_dir_check=working_dir_check)
        module_name = module_name or module_file.stem
        module = __load_module(module_name, module_file)
    elif module_name is not None:
        module = importlib.import_module(module_name)
    elif default_module is None:
        module, module_name = importlib.import_module("builtins"), "builtins"
    else:
        module, module_name = default_module, default_module.__name__
    validate_import(module_name, target)
    validate_attribute(
        f"{module_name}.{target}",
        protected_member_check=protected_member_check,
        private_member_check=private_member_check,
        ascii_check=ascii_check,
    )
    if hasattr(module, target):
        return getattr(module, target)
    raise ImportError(f'Target "{target}" not found in module "{module_name}".')


def load_yaml(
    yaml_file: PathLike,
    *,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
) -> dict[str, Any]:
    """Load a yaml file.

    Args:
        yaml_file (PathLike): Path to the yaml file.
        hidden_check (Optional[bool]): Whether to block paths with hidden directories (starting with '.').
            Default is taken from global settings.
        working_dir_check (Optional[bool]): Whether to ensure that relative paths resolve within allowed directories.
            Default is taken from global settings.

    Returns:
        Loaded yaml file.
    """
    yaml_file = check_path(yaml_file, hidden_check=hidden_check, working_dir_check=working_dir_check)
    with open(yaml_file, encoding="utf-8") as fin:
        return YAML(typ="safe", pure=True).load(fin)  # YAML 1.2 support
